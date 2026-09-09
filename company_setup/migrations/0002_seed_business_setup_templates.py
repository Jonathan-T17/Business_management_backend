from django.db import migrations


TEMPLATES = [
    ("general", "General Business", "A practical starting point for most companies.", {"departments": ["Finance", "Human Resources", "Operations"], "positions": ["Manager", "Employee"], "document_categories": ["General", "Policies"]}),
    ("manufacturing", "Manufacturing", "Production, quality, maintenance, and warehouse operations.", {"departments": ["Production", "Quality", "Maintenance", "Warehouse", "Finance", "Human Resources"], "positions": ["Production Operator", "Production Supervisor", "Quality Officer", "Maintenance Technician"], "document_categories": ["Policies", "SOPs", "Quality", "Maintenance"]}),
    ("retail", "Retail", "Store operations, sales, stock, and customer service.", {"departments": ["Sales", "Stock", "Finance", "Human Resources"], "positions": ["Store Manager", "Sales Associate", "Stock Controller"], "document_categories": ["Policies", "Stock", "Sales"]}),
    ("logistics", "Logistics", "Transport, warehouse, and delivery operations.", {"departments": ["Transport", "Warehouse", "Operations", "Finance"], "positions": ["Operations Manager", "Driver", "Warehouse Officer"], "document_categories": ["Policies", "Delivery", "Warehouse"]}),
    ("agriculture", "Agriculture", "Farm production, quality, and field operations.", {"departments": ["Production", "Quality", "Field Operations", "Finance"], "positions": ["Farm Supervisor", "Field Officer", "Quality Officer"], "document_categories": ["Policies", "Production", "Quality"]}),
    ("construction", "Construction", "Project, site, safety, and procurement operations.", {"departments": ["Projects", "Site Operations", "Safety", "Procurement", "Finance"], "positions": ["Project Manager", "Site Supervisor", "Safety Officer"], "document_categories": ["Policies", "Safety", "Project Documents"]}),
    ("professional-services", "Professional Services", "Client delivery, finance, and people operations.", {"departments": ["Client Services", "Finance", "Human Resources"], "positions": ["Account Manager", "Consultant", "Finance Officer"], "document_categories": ["Policies", "Client Documents", "Contracts"]}),
]


def seed_templates(apps, schema_editor):
    template_model = apps.get_model("company_setup", "BusinessSetupTemplate")
    for code, name, description, configuration in TEMPLATES:
        template_model.objects.update_or_create(
            code=code,
            defaults={
                "name": name,
                "description": description,
                "configuration": configuration,
                "is_active": True,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ("company_setup", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_templates, migrations.RunPython.noop),
    ]