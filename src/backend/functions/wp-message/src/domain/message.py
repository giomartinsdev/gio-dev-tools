from dataclasses import dataclass


@dataclass(frozen=True)
class WhatsAppMessage:
    number: str
    text: str

    def __post_init__(self):
        if not self.number or not self.number.strip():
            raise ValueError("number is required")
        if not self.text or not self.text.strip():
            raise ValueError("message is required")
