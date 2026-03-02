import io
from django.template.loader import get_template
from xhtml2pdf import pisa


def render_html_to_pdf_bytes(template_src, context_dict=None):
    """
    Rend un template HTML en PDF (bytes) avec xhtml2pdf.
    Retourne None en cas d'erreur.
    """
    if context_dict is None:
        context_dict = {}

    template = get_template(template_src)
    html = template.render(context_dict)

    result = io.BytesIO()
    pdf = pisa.pisaDocument(io.BytesIO(html.encode("UTF-8")), result)

    if pdf.err:
        return None

    return result.getvalue()