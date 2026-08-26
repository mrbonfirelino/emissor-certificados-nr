from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class SignatureData:
    signer_name: str
    signer_cpf: str
    timestamp: datetime
    certificate_serial: Optional[str] = None  # Futuro: ICP-Brasil
    image_path: Optional[str] = None          # Assinatura visual (PNG)


class SignatureProvider(ABC):
    """Interface para provedores de assinatura."""
    
    @abstractmethod
    def sign(self, pdf_path: str, data: SignatureData) -> str:
        """Assina PDF e retorna caminho do PDF assinado."""
        pass
    
    @abstractmethod
    def verify(self, pdf_path: str) -> bool:
        """Verifica assinatura do PDF."""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Nome do provedor (ex: 'Local', 'ICP-Brasil')."""
        pass