import pyinstaller_versionfile

pyinstaller_versionfile.create_versionfile(
    output_file="versionfile.txt",
    version="1.2.3.4",
    company_name="Multispan Control Instruments Pvt Ltd",
    file_description="Remote Desktop application",
    internal_name="Remote Desktop application",
    legal_copyright="© 2023 MULTISPAN. All rights reserved.",
    original_filename="client.exe",
    product_name="Remote Desktop application"
)