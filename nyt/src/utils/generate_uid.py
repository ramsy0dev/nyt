import uuid
import hashlib
import string
import random

def generate_uid(data: str) -> str:
    """
    Generates a UID.

    Args:
        data (str): Random data that will be used to generate the UID.
    
    Returns:
        str: the generated uid.
    """

    data = f"{data}{''.join([char for char in random.choices(string.ascii_letters)])}" # Adding random charachters to the data

    hashed_username_salt = hashlib.md5(data.encode()).hexdigest()
    generated_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, hashed_username_salt)

    return str(generated_uuid)

