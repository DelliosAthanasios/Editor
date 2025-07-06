        def make_btn(icon, tooltip, slot, text=None):
            btn = QToolButton()
            if icon:
                btn.setIcon(QIcon(icon))
            if text:
                btn.setText(text)
            btn.setToolTip(tooltip)
            btn.setFixedSize(28, 28)
            btn.clicked.connect(slot)
            return btn
        open_btn = make_btn(self.style().standardIcon(QStyle.SP_DialogOpenButton), "Open PDF", self.parent_viewer.open_pdf)
        prev_btn = make_btn(self.style().standardIcon(QStyle.SP_ArrowLeft), "Previous Page", self.prev_page)
        next_btn = make_btn(self.style().standardIcon(QStyle.SP_ArrowRight), "Next Page", self.next_page)
        zoom_out_btn = make_btn(None, "Zoom Out", self.zoom_out, text="−")
        zoom_in_btn = make_btn(None, "Zoom In", self.zoom_in, text="+") 