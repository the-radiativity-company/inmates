from io import BytesIO
from io import StringIO
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfinterp import PDFPageInterpreter
from pdfminer.pdfinterp import PDFResourceManager
from pdfminer.pdfpage import PDFPage
from scrapy import Spider
from subprocess import run as run_proc


class AdamsRoster(Spider):
    name = 'adams'

    def parse(self, response):
        pass


def handle_pdf(buffer: BytesIO, codec: str = 'utf-8'):
    rsrcmgr = PDFResourceManager()  # shared context for resources
    sio = StringIO()
    laparams = LAParams()  # "layout params" for formatting output
    device = TextConverter(rsrcmgr, sio, codec=codec, laparams=laparams)
    interpreter = PDFPageInterpreter(rsrcmgr, device)

    for page in PDFPage.get_pages(buffer):
        interpreter.process_page(page)

    text = sio.getvalue()

    device.close()
    sio.close()

    return text
