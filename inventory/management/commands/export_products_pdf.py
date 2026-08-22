from django.core.management.base import BaseCommand
from django.conf import settings
from decimal import Decimal
import os

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

from inventory.models import Product


class Command(BaseCommand):
    help = "Export product price list (with discounts) to a PDF file"

    def handle(self, *args, **options):
        products = Product.objects.filter(is_active=True).order_by('name')

        out_dir = settings.MEDIA_ROOT if getattr(settings, 'MEDIA_ROOT', None) else settings.BASE_DIR
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, 'product_price_list.pdf')

        doc = SimpleDocTemplate(out_path, pagesize=A4)
        styles = getSampleStyleSheet()

        elems = []
        elems.append(Paragraph('Product Price List', styles['Title']))
        elems.append(Spacer(1, 12))

        data = [['#', 'Product Name', 'MRP (₹)', 'Discount (₹)', 'Price After Discount (₹)']]

        for i, p in enumerate(products, start=1):
            mrp = Decimal(p.price)
            # Match frontend logic: discount = mrp * 0.80 (i.e., 80% of MRP shown as discount)
            discount = (mrp * Decimal('0.80')).quantize(Decimal('0.01'))
            after = (mrp - discount).quantize(Decimal('0.01'))

            data.append([
                str(i),
                p.name,
                f"{mrp:.2f}",
                f"{discount:.2f}",
                f"{after:.2f}",
            ])

        table = Table(data, colWidths=[30, 260, 80, 80, 100])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f2f2f2')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#111111')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ]))

        elems.append(table)

        doc.build(elems)

        self.stdout.write(self.style.SUCCESS(f'Exported {len(products)} products to {out_path}'))
