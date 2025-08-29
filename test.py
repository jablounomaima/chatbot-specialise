import pdfkit

# 🔽 Spécifie le chemin vers wkhtmltopdf.exe
path_wkhtmltopdf = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'

config = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)

# Génère le PDF
pdfkit.from_string("<h1>Test PDF</h1>", "test.pdf", configuration=config)

print("✅ PDF généré avec succès !")