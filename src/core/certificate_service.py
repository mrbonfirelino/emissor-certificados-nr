import json
from datetime import date
from pathlib import Path
from typing import Optional, Dict, Any
from src.core.models import (
    CertificateData, CertificateRecord, NRTemplate, CompanyConfig, Employee
)
from src.core.history_repo import HistoryRepository
from src.core.employee_repo import EmployeeRepository
from src.core.template_loader import load_nr_template
from src.core.config import load_company_config
from src.core.pdf_generator import generate_certificate_pdf
from src.utils.paths import get_data_dir, get_certificados_dir
from src.utils.date_utils import hoje


def _pasta_funcionario(employee) -> str:
    """Subpasta do funcionario em data/certificados (CPF so em colisao)."""
    from src.utils.folder_utils import employee_folder_name
    from src.core.employee_repo import EmployeeRepository
    return employee_folder_name(employee, EmployeeRepository().get_all(limit=1000000))


class CertificateService:
    def __init__(self):
        self.history = HistoryRepository()
        self.employees = EmployeeRepository()
        self.company_config = load_company_config()

    def refresh_config(self):
        self.company_config = load_company_config()

    def generate_certificate(
        self,
        nr_code: str,
        employee: Employee,
        data_treinamento: date,
        carga_horaria: int,
        descricao_treinamento: str,
        campos_extra: Dict[str, str],
        output_dir: Optional[Path] = None,
        validade_meses: Optional[int] = None
    ) -> Optional[Path]:
        if not self.company_config:
            raise ValueError("Empresa nao configurada.")

        template = load_nr_template(nr_code)
        if not template:
            raise ValueError(f"Template {nr_code} nao encontrado")

        if carga_horaria < template.carga_horaria_minima:
            raise ValueError(f"Carga horaria minima para {nr_code} e {template.carga_horaria_minima}h")

        cert_number = self.history.next_certificate_number()

        # opcao: imprimir data/hora da emissao junto ao numero (Configuracoes)
        data_hora_impressao = ""
        try:
            from src.core.app_settings import get_setting
            if get_setting("pdf_data_hora_emissao", False):
                from datetime import datetime as _dt
                data_hora_impressao = _dt.now().strftime("%d/%m/%Y %H:%M")
        except Exception:
            pass

        cert_data = CertificateData(
            cert_number=cert_number,
            nr_code=template.nr_code,
            nr_name=template.nr_name,
            funcionario_nome=employee.nome,
            funcionario_cpf=employee.cpf,
            empresa_nome=self.company_config.empresa_nome,
            empresa_cnpj=self.company_config.empresa_cnpj,
            local_treinamento=self.company_config.local_treinamento,
            instrutor_nome=self.company_config.instrutor_nome,
            instrutor_registro_mte=self.company_config.instrutor_registro_mte,
            data_treinamento=data_treinamento,
            carga_horaria=carga_horaria,
            descricao_treinamento=descricao_treinamento,
            campos_extra=campos_extra,
            conteudo_programatico=template.conteudo_programatico,
            assinaturas=template.assinaturas,
            data_hora_impressao=data_hora_impressao
        )

        output_dir = output_dir or get_certificados_dir() / _pasta_funcionario(employee) / template.nr_code
        output_dir.mkdir(parents=True, exist_ok=True)
        pdf_filename = f"{cert_number}_{nr_code}_{employee.nome.replace(' ', '_')}.pdf"
        pdf_path = output_dir / pdf_filename

        # templates PPTX da tecnica (templates/certificados_pptx/NR-XX.pptx)
        # tem prioridade; sem PowerPoint/COM o fluxo JSON/ReportLab continua
        from src.core import pptx_certificate_service as pptx_cert
        if pptx_cert.get_pptx_template_path(nr_code):
            pptx_cert.gerar_pdf_pptx(
                nr_code, employee, data_treinamento, cert_number, pdf_path,
                data_hora=data_hora_impressao
            )
        else:
            generate_certificate_pdf(cert_data, template, pdf_path)

        record = CertificateRecord(
            cert_number=cert_number,
            nr_code=template.nr_code,
            employee_id=employee.id,
            funcionario_nome=employee.nome,
            funcionario_cpf=employee.cpf,
            data_inicio=data_treinamento.isoformat(),
            data_fim=data_treinamento.isoformat(),
            carga_horaria=carga_horaria,
            descricao_treinamento=descricao_treinamento,
            campos_extra=json.dumps(campos_extra, ensure_ascii=False),
            pdf_path=str(pdf_path),
            validade_meses=validade_meses
        )
        self.history.save(record)

        # espelha na pasta de rede (best-effort, nao bloqueia emissao)
        try:
            from src.core import network_sync
            salvo = self.history.get_by_number(cert_number)
            if salvo:
                network_sync.run_async(network_sync.sync_certificate, salvo, employee)
        except Exception:
            pass

        return pdf_path

    def generate_preview_pdf(
        self,
        nr_code: str,
        employee: Employee,
        data_treinamento: date,
        carga_horaria: int,
        descricao_treinamento: str,
        campos_extra: Dict[str, str],
        output_path: Path
    ) -> Optional[Path]:
        if not self.company_config:
            return None

        template = load_nr_template(nr_code)
        if not template:
            return None

        cert_data = CertificateData(
            cert_number="PREVIEW-000000",
            nr_code=template.nr_code,
            nr_name=template.nr_name,
            funcionario_nome=employee.nome,
            funcionario_cpf=employee.cpf,
            empresa_nome=self.company_config.empresa_nome,
            empresa_cnpj=self.company_config.empresa_cnpj,
            local_treinamento=self.company_config.local_treinamento,
            instrutor_nome=self.company_config.instrutor_nome,
            instrutor_registro_mte=self.company_config.instrutor_registro_mte,
            data_treinamento=data_treinamento,
            carga_horaria=carga_horaria,
            descricao_treinamento=descricao_treinamento,
            campos_extra=campos_extra,
            conteudo_programatico=template.conteudo_programatico,
            assinaturas=template.assinaturas
        )

        generate_certificate_pdf(cert_data, template, output_path)
        return output_path

    def get_certificate_data_for_preview(
        self,
        nr_code: str,
        employee: Employee,
        data_treinamento: date,
        carga_horaria: int,
        descricao_treinamento: str,
        campos_extra: Dict[str, str]
    ) -> Optional[CertificateData]:
        if not self.company_config:
            return None
        template = load_nr_template(nr_code)
        if not template:
            return None

        return CertificateData(
            cert_number="PREVIEW-000000",
            nr_code=template.nr_code,
            nr_name=template.nr_name,
            funcionario_nome=employee.nome,
            funcionario_cpf=employee.cpf,
            empresa_nome=self.company_config.empresa_nome,
            empresa_cnpj=self.company_config.empresa_cnpj,
            local_treinamento=self.company_config.local_treinamento,
            instrutor_nome=self.company_config.instrutor_nome,
            instrutor_registro_mte=self.company_config.instrutor_registro_mte,
            data_treinamento=data_treinamento,
            carga_horaria=carga_horaria,
            descricao_treinamento=descricao_treinamento,
            campos_extra=campos_extra,
            conteudo_programatico=template.conteudo_programatico,
            assinaturas=template.assinaturas
        )
