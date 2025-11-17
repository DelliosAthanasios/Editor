import webview

def start_app():
    window = webview.create_window(
        "PDF Reader",
        "pdf_reader_ui.html",
        width=1200,
        height=900
    )
    webview.start()

if __name__ == "__main__":
    start_app()