#include "mupdf/fitz.h"
#include <stdio.h>

int main(int argc, char **argv) {
    if (argc < 2) {
        printf("Usage: %s file.pdf\n", argv[0]);
        return 1;
    }

    const char *filename = argv[1];

    fz_context *ctx = fz_new_context(NULL, NULL, FZ_STORE_UNLIMITED);
    if (!ctx) {
        fprintf(stderr, "Cannot create MuPDF context\n");
        return 1;
    }

    fz_register_document_handlers(ctx);

    fz_document *doc = fz_open_document(ctx, filename);
    if (!doc) {
        fprintf(stderr, "Cannot open PDF: %s\n", filename);
        fz_drop_context(ctx);
        return 1;
    }

    int page_count = fz_count_pages(ctx, doc);
    printf("Total pages: %d\n", page_count);

    for (int i = 0; i < page_count; i++) {
        fz_page *page = fz_load_page(ctx, doc, i);
        fz_rect bounds = fz_bound_page(ctx, page);
        fz_text_page *text = fz_new_text_page(ctx, bounds);
        fz_device *dev = fz_new_text_device(ctx, text, NULL);

        fz_run_page(ctx, page, dev, fz_identity, NULL);
        fz_text_page_write_text(ctx, text, stdout, NULL);

        fz_drop_device(ctx, dev);
        fz_drop_text_page(ctx, text);
        fz_drop_page(ctx, page);
    }

    fz_drop_document(ctx, doc);
    fz_drop_context(ctx);
    return 0;
}
