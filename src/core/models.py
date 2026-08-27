from datetime import date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator
from src.utils.validators import validar_cpf, validar_cnpj, validar_registro_mte, formatar_cpf, formatar_cnpj, formatar_registro_mte


class CompanyConfig(BaseModel):
    empresa_nome: str = Field(..., min_length=2)
    empresa_cnpj: str = Field(..., min_length=14)
    local_treinamento: str = Field(..., min_length=2)
    instrutor_nome: str = Field(..., min_length=2)
    instrutor_registro_mte: str = Field(...)

    @field_validator('empresa_cnpj')
    @classmethod
    def validar_cnpj_empresa(cls, v: str) -> str:
        if not validar_cnpj(v):
            raise ValueError("CNPJ invalido")
        return formatar_cnpj(v)

    @field_validator('instrutor_registro_mte')
    @classmethod
    def validar_registro_mte_instrutor(cls, v: str) -> str:
        if not validar_registro_mte(v):
            raise ValueError("Registro MTE invalido (formato: MTE 44633/RJ)")
        return formatar_registro_mte(v)


class Employee(BaseModel):
    id: Optional[int] = None
    nome: str = Field(..., min_length=2)
    cpf: Optional[str] = None
    funcao: Optional[str] = None
    created_at: Optional[str] = None

    @field_validator('cpf')
    @classmethod
    def validar_cpf_funcionario(cls, v: Optional[str]) -> Optional[str]:
        if not v or not v.strip():
            return None
        if not validar_cpf(v):
            raise ValueError("CPF invalido")
        return formatar_cpf(v)

    def display_name(self) -> str:
        if self.cpf:
            return f"{self.nome} ({self.cpf})"
        return self.nome


class NRTemplateExtraField(BaseModel):
    id: str
    label: str
    tipo: str = "text"  # text, select, number
    obrigatorio: bool = False
    placeholder: str = ""
    opcoes: List[str] = []


class NRTemplate(BaseModel):
    nr_code: str = Field(..., pattern=r'^[A-Z][A-Z0-9-]+$')
    nr_name: str
    carga_horaria_minima: int = 8
    validade_meses: int = 12
    riscos: List[str] = []
    descricao_padrao: str
    campos_extra: List[NRTemplateExtraField] = []
    conteudo_programatico: List[str] = []
    texto_certificado: str
    assinaturas: List[Dict[str, Any]] = []


class LayoutConfig(BaseModel):
    page_size: str = "A4"
    orientation: str = "landscape"
    margins: Dict[str, int] = {"top": 10, "bottom": 10, "left": 10, "right": 10}
    logo: Dict[str, Any] = {"path": "assets/LOGO TIPO ALTEC.png", "width": 28, "height": 18, "position": "top-left"}
    fonts: Dict[str, Dict[str, Any]] = {
        "title": {"family": "Helvetica-Bold", "size": 26, "color": "#1B3A5C", "leading_multiplier": 1.3, "space_after": 4},
        "subtitle": {"family": "Helvetica-Bold", "size": 14, "color": "#1B3A5C", "leading_multiplier": 1.4, "space_after": 4},
        "body": {"family": "Helvetica", "size": 11, "color": "#333333"},
        "body_bold": {"family": "Helvetica-Bold", "size": 13, "color": "#333333", "leading_multiplier": 1.5, "space_after": 6},
        "small": {"family": "Helvetica", "size": 8, "color": "#999999", "leading_multiplier": 1.4},
        "signature": {"family": "Helvetica", "size": 10, "color": "#333333", "leading_multiplier": 1.5},
        "signature_bold": {"family": "Helvetica-Bold", "size": 10, "color": "#333333"},
        "signature_detail": {"family": "Helvetica", "size": 8, "color": "#999999"},
        "content_item": {"family": "Helvetica-Bold", "size": 12, "color": "#333333", "leading_multiplier": 1.4, "space_after": 3, "left_indent_mm": 5}
    }
    colors: Dict[str, str] = {
        "primary": "#1B3A5C", "text": "#333333", "muted": "#999999", "divider": "#1B3A5C"
    }
    certificate_number: Dict[str, Any] = {
        "position": "bottom-right", "font_size": 7, "color": "#CCCCCC", "prefix": "CERT-"
    }
    signature_blocks: List[Dict[str, Any]] = [
        {"role": "instrutor", "label": "INSTRUTOR/RESPONSAVEL TECNICO", "registro_label": "Registro MTE"},
        {"role": "participante", "label": "PARTICIPANTE", "registro_label": ""}
    ]
    signature_block: Dict[str, Any] = {
        "label_size": 10, "name_size": 10, "detail_size": 8, "detail_color": "#000000"
    }
    spacers: Dict[str, Any] = {
        "after_header_mm": 4, "after_divider_mm": 8, "after_text_mm": 8,
        "after_date_mm": 0, "after_content_title_mm": 6, "cert_number_mm": 4
    }
    border: Dict[str, Any] = {"inset_mm": 5, "line_width": 2}
    divider: Dict[str, Any] = {"line_width": 2}
    city: str = "Cordeiro"
    title_format: str = "CERTIFICADO - NR{nr_num}"
    content_title: str = "CONTEUDO PROGRAMATICO"
    signature_line_length: int = 55
    content_columns: Dict[str, Any] = {"count": 1, "padding_mm": 5}


class CertificateData(BaseModel):
    cert_number: str
    nr_code: str
    nr_name: str
    funcionario_nome: str
    funcionario_cpf: str
    empresa_nome: str
    empresa_cnpj: str
    local_treinamento: str
    instrutor_nome: str
    instrutor_registro_mte: str
    data_treinamento: date
    carga_horaria: int
    descricao_treinamento: str
    campos_extra: Dict[str, str] = {}
    conteudo_programatico: List[str] = []
    assinaturas: List[Dict[str, Any]] = []

    def to_dict(self) -> Dict[str, Any]:
        meses_pt = {
            1: "janeiro", 2: "fevereiro", 3: "marco", 4: "abril",
            5: "maio", 6: "junho", 7: "julho", 8: "agosto",
            9: "setembro", 10: "outubro", 11: "novembro", 12: "dezembro"
        }
        d = self.data_treinamento
        data_extensa = f"{d.day} de {meses_pt[d.month]} de {d.year}"

        return {
            "cert_number": self.cert_number,
            "nr_code": self.nr_code,
            "nr_code_num": self.nr_code.replace("NR-", ""),
            "nr_name": self.nr_name,
            "nome_funcionario": self.funcionario_nome,
            "cpf": self.funcionario_cpf,
            "empresa": self.empresa_nome,
            "cnpj": self.empresa_cnpj,
            "local_treinamento": self.local_treinamento,
            "instrutor_nome": self.instrutor_nome,
            "instrutor_registro_mte": self.instrutor_registro_mte,
            "data_treinamento": data_extensa,
            "carga_horaria": str(self.carga_horaria),
            "descricao_treinamento": self.descricao_treinamento,
            **self.campos_extra
        }


class CertificateRecord(BaseModel):
    id: Optional[int] = None
    cert_number: str
    nr_code: str
    employee_id: int
    funcionario_nome: str
    funcionario_cpf: str
    data_inicio: str
    data_fim: str
    carga_horaria: int
    descricao_treinamento: str
    campos_extra: str
    pdf_path: Optional[str] = None
    created_at: Optional[str] = None
