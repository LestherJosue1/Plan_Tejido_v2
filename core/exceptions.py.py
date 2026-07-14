class ManufacturingError(Exception):
    """Clase base para excepciones del dominio de manufactura."""
    pass

class InvalidSchemaError(ManufacturingError):
    """Se lanza cuando los datos de entrada no cumplen con las columnas requeridas."""
    pass

class ConfigurationError(ManufacturingError):
    """Se lanza cuando los parámetros de producción son inválidos."""
    pass