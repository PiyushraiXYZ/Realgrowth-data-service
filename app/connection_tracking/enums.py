from enum import Enum


class ConnectionStatus(str, Enum):
    INITIATED = "INITIATED"
    SENT = "SENT"
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"
    FAILED = "FAILED"


class ConnectionPlatform(str, Enum):
    LINKEDIN = "linkedin"
    EMAIL = "email"
    EXTERNAL_WEBSITE = "external_website"


class ConnectionEventSource(str, Enum):
    BROWSER_EXTENSION = "browser_extension"
    MANUAL = "manual"
    API = "api"