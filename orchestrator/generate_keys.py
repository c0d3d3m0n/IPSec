from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
import os

def generate_keys(directory="keys"):
    if not os.path.exists(directory):
        os.makedirs(directory)
        
    private_key_path = os.path.join(directory, "private_key.pem")
    public_key_path = os.path.join(directory, "public_key.pem")

    if os.path.exists(private_key_path):
        print("Keys already exist. Skipping.")
        return

    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    # Serialize private key
    with open(private_key_path, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))

    # Generate public key
    public_key = private_key.public_key()

    # Serialize public key
    with open(public_key_path, "wb") as f:
        f.write(public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ))
    
    print(f"Keys generated in {directory}/")

if __name__ == "__main__":
    generate_keys()
