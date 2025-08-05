import webview
import fitz  # PyMuPDF
import base64
import json
import os

pdf_handler = None

class PDFHandler:
    def __init__(self):
        self.doc = None
        self.file_path = None
        self.current_page = 0
        self.zoom = 1.0
        self.rotation = 0

    def load_pdf(self, file_path):
        try:
            self.doc = fitz.open(file_path)
            self.file_path = file_path
            self.current_page = 0
            self.zoom = 1.0
            self.rotation = 0
            return {
                "success": True,
                "fileName": os.path.basename(file_path),
                "totalPages": self.doc.page_count
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def goToPage(self, page_num):
        if self.doc:
            page_num = int(page_num) - 1
            if 0 <= page_num < self.doc.page_count:
                self.current_page = page_num
                return {"success": True}
        return {"success": False}

    def setZoom(self, zoom_percent):
        try:
            self.zoom = float(zoom_percent) / 100.0
            return {"success": True}
        except Exception:
            return {"success": False}

    def fitToWidth(self):
        if self.doc:
            page = self.doc.load_page(self.current_page)
            width = page.rect.width
            self.zoom = 600 / width
            return {"success": True, "newZoom": int(self.zoom * 100)}
        return {"success": False}

    def rotatePage(self, rotation):
        try:
            self.rotation = int(rotation)
            return {"success": True}
        except Exception:
            return {"success": False}

    def downloadPDF(self):
        if self.file_path and os.path.exists(self.file_path):
            with open(self.file_path, "rb") as f:
                data = f.read()
                b64 = base64.b64encode(data).decode("utf-8")
                return {"success": True, "base64": b64, "fileName": os.path.basename(self.file_path)}
        return {"success": False}

    def printPDF(self):
        return {"success": False, "error": "Printing not implemented"}

    def getThumbnails(self):
        if self.doc:
            thumbs = []
            for i in range(self.doc.page_count):
                page = self.doc.load_page(i)
                pix = page.get_pixmap(matrix=fitz.Matrix(0.25, 0.25).preRotate(self.rotation))
                img_bytes = pix.tobytes("png")
                b64 = base64.b64encode(img_bytes).decode("utf-8")
                thumbs.append({
                    "image": f"data:image/png;base64,{b64}",
                    "page": i + 1
                })
            return thumbs
        return []

    def getOutline(self):
        if self.doc:
            outline = []
            for item in self.doc.get_toc():
                outline.append({
                    "title": item[1],
                    "page": item[2]
                })
            return outline
        return []

    def search(self, query):
        if self.doc:
            results = []
            for i in range(self.doc.page_count):
                page = self.doc.load_page(i)
                text_instances = page.search_for(query)
                text = page.get_text()
                if text_instances:
                    for inst in text_instances:
                        snippet = text[max(0, int(inst.y0)-80): int(inst.y1)+80]
                        results.append({
                            "page": i + 1,
                            "text": snippet
                        })
            return results
        return []

    def renderPage(self):
        if self.doc:
            page = self.doc.load_page(self.current_page)
            zoom_matrix = fitz.Matrix(self.zoom, self.zoom).preRotate(self.rotation)
            pix = page.get_pixmap(matrix=zoom_matrix)
            img_bytes = pix.tobytes("png")
            b64 = base64.b64encode(img_bytes).decode("utf-8")
            return {
                "image": f"data:image/png;base64,{b64}",
                "page": self.current_page + 1,
                "totalPages": self.doc.page_count
            }
        return None

class ApiBridge:
    def openFile(self):
        global pdf_handler
        # Use pywebview dialog API, always from main thread
        file_paths = webview.windows[0].create_file_dialog(
            webview.OPEN_DIALOG,
            allow_multiple=False,
            file_types=[('PDF files (*.pdf)', '*.pdf')]
        )
        if file_paths and len(file_paths) > 0:
            file_path = file_paths[0]
            result = pdf_handler.load_pdf(file_path)
            if result["success"]:
                webview.windows[0].evaluate_js(
                    f'window.uiInterface.updateFileName("{result["fileName"]}")'
                )
                webview.windows[0].evaluate_js(
                    f'window.uiInterface.updatePageInfo(1, {result["totalPages"]})'
                )
                thumbs = pdf_handler.getThumbnails()
                webview.windows[0].evaluate_js(
                    f'window.uiInterface.updateThumbnails({json.dumps(thumbs)})'
                )
                outline = pdf_handler.getOutline()
                webview.windows[0].evaluate_js(
                    f'window.uiInterface.updateOutline({json.dumps(outline)})'
                )
                self.updatePage()
            else:
                webview.windows[0].evaluate_js(
                    f'showNotification("{result.get("error", "Failed to open file")}", "error")'
                )
        else:
            webview.windows[0].evaluate_js(
                'showNotification("No file selected", "error")'
            )

    def goToPage(self, page_num):
        global pdf_handler
        res = pdf_handler.goToPage(page_num)
        if res["success"]:
            self.updatePage()
        else:
            webview.windows[0].evaluate_js('showNotification("Invalid page", "error")')

    def setZoom(self, zoom_percent):
        global pdf_handler
        res = pdf_handler.setZoom(zoom_percent)
        if res["success"]:
            self.updatePage()

    def fitToWidth(self):
        global pdf_handler
        res = pdf_handler.fitToWidth()
        if res["success"]:
            webview.windows[0].evaluate_js(
                f'document.getElementById("zoomInput").value = "{res["newZoom"]}%";'
            )
            self.updatePage()

    def rotatePage(self, rotation):
        global pdf_handler
        res = pdf_handler.rotatePage(rotation)
        if res["success"]:
            self.updatePage()

    def downloadPDF(self):
        global pdf_handler
        res = pdf_handler.downloadPDF()
        if res["success"]:
            js = (
                "const a = document.createElement('a');"
                f"a.href = 'data:application/pdf;base64,{res['base64']}';"
                f"a.download = '{res['fileName']}';"
                "a.click();"
            )
            webview.windows[0].evaluate_js(js)
        else:
            webview.windows[0].evaluate_js('showNotification("Download failed", "error")')

    def printPDF(self):
        webview.windows[0].evaluate_js('showNotification("Print not implemented", "error")')

    def search(self, query):
        global pdf_handler
        results = pdf_handler.search(query)
        webview.windows[0].evaluate_js(
            f'window.uiInterface.updateSearchResults({json.dumps(results)})'
        )

    def updatePage(self):
        global pdf_handler
        page_data = pdf_handler.renderPage()
        if page_data:
            js = (
                f'document.getElementById("pdfViewer").innerHTML = '
                f'"<img src=\'{page_data["image"]}\' style=\'max-width:100%;max-height:80vh;border-radius:12px;box-shadow:0 8px 32px rgba(0,0,0,0.1);\' />";'
            )
            webview.windows[0].evaluate_js(js)
            webview.windows[0].evaluate_js(
                f'window.uiInterface.updatePageInfo({page_data["page"]}, {page_data["totalPages"]})'
            )

def start_app():
    global pdf_handler
    pdf_handler = PDFHandler()
    api = ApiBridge()
    window = webview.create_window(
        "PDF Reader",
        "pdf_reader_ui.html",
        js_api=api,
        width=1200,
        height=900
    )
    webview.start()

if __name__ == "__main__":
    start_app()