from src.core.signature.base import SignatureProvider, SignatureData


class LocalSignatureProvider(SignatureProvider):
    """Provedor local (placeholder - apenas salva metadata, não assina criptograficamente)."""
    
    @property
    def name(self) -> str:
        return "Local (Imagem)"
    
    def sign(self, pdf_path: str, data: SignatureData) -> str:
        """
        Placeholder: No futuro, aqui colocaria a imagem da assinatura no PDF.
        Por enquanto, apenas retorna o mesmo caminho (sem alteração).
        """
        return pdf_path
    
    def verify(self, pdf_path: str) -> bool:
        """Placeholder: sempre retorna True (sem verificação criptográfica)."""
        return True


# Instância singleton
local_provider = LocalSignatureProvider()