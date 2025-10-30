(function () {
    function ready(callback) {
        if (document.readyState !== 'loading') {
            callback();
            return;
        }
        document.addEventListener('DOMContentLoaded', callback);
    }

    function getField(selector) {
        return document.querySelector(selector);
    }

    function sanitizeHtml(html) {
        if (!html) {
            return '';
        }
        return html.replace(/<script[^>]*>.*?<\/script>/gi, '');
    }

    function normalizeUrl(value) {
        if (!value) {
            return '#';
        }

        try {
            const url = new URL(value, window.location.origin);
            return url.href;
        } catch (error) {
            return value;
        }
    }

    function updatePreviewFactory(root, fields) {
        const titleEl = root.querySelector('[data-preview-title]');
        const summaryEl = root.querySelector('[data-preview-summary]');
        const badgeEl = root.querySelector('[data-preview-badge]');
        const dateEl = root.querySelector('[data-preview-date]');
        const linkEl = root.querySelector('[data-preview-link]');
        const linkLabelEl = root.querySelector('[data-preview-link-label]');

        const defaults = {
            title: 'Título do cartão',
            summary:
                '<p>Utilize o campo “Resumo” para adicionar o conteúdo que aparecerá no site.</p>',
            link: 'Texto do link',
        };

        return function updatePreview() {
            const title = fields.title && fields.title.value.trim();
            const badge = fields.badge && fields.badge.value.trim();
            const date = fields.displayDate && fields.displayDate.value.trim();
            const linkLabel = fields.linkLabel && fields.linkLabel.value.trim();
            const linkUrl = fields.linkUrl && fields.linkUrl.value.trim();

            if (titleEl) {
                titleEl.textContent = title || defaults.title;
            }

            if (summaryEl) {
                const editor = window.CKEDITOR && fields.summary && fields.summary.id
                    ? window.CKEDITOR.instances[fields.summary.id]
                    : null;

                const summaryValue = editor ? editor.getData() : fields.summary?.value || '';
                const content = sanitizeHtml(summaryValue).trim();
                summaryEl.innerHTML = content || defaults.summary;
            }

            if (badgeEl) {
                if (badge) {
                    badgeEl.textContent = badge;
                    badgeEl.removeAttribute('hidden');
                } else {
                    badgeEl.setAttribute('hidden', '');
                }
            }

            if (dateEl) {
                if (date) {
                    dateEl.textContent = date;
                    dateEl.removeAttribute('hidden');
                } else {
                    dateEl.setAttribute('hidden', '');
                }
            }

            if (linkEl && linkLabelEl) {
                if (linkLabel) {
                    linkLabelEl.textContent = linkLabel;
                    linkEl.setAttribute('href', normalizeUrl(linkUrl));
                    linkEl.removeAttribute('hidden');
                } else {
                    linkLabelEl.textContent = defaults.link;
                    linkEl.setAttribute('href', '#');
                    linkEl.setAttribute('hidden', '');
                }
            }
        };
    }

    function bindInput(field, handler) {
        if (!field) {
            return;
        }
        field.addEventListener('input', handler);
        field.addEventListener('change', handler);
    }

    function bindCkEditor(handler, textarea) {
        if (!window.CKEDITOR || !textarea || !textarea.id) {
            return;
        }

        const instance = window.CKEDITOR.instances[textarea.id];
        if (!instance) {
            return;
        }

        instance.on('change', handler);
        instance.on('dataReady', handler);
        instance.on('instanceReady', handler);
    }

    ready(function () {
        const root = document.querySelector('[data-section-item-preview]');
        if (!root) {
            return;
        }

        const fields = {
            title: getField('[name="title"]'),
            summary: getField('[name="summary"]'),
            badge: getField('[name="badge"]'),
            displayDate: getField('[name="display_date"]'),
            linkLabel: getField('[name="link_label"]'),
            linkUrl: getField('[name="link_url"]'),
        };

        const updatePreview = updatePreviewFactory(root, fields);

        Object.values(fields).forEach(function (field) {
            bindInput(field, updatePreview);
        });

        if (window.refreshRichTextEditors) {
            window.refreshRichTextEditors();
        }

        if (fields.summary) {
            if (window.CKEDITOR && fields.summary.id && window.CKEDITOR.instances[fields.summary.id]) {
                bindCkEditor(updatePreview, fields.summary);
            } else if (window.CKEDITOR) {
                window.CKEDITOR.on('instanceReady', function (event) {
                    if (event.editor.element && event.editor.element.$ === fields.summary) {
                        bindCkEditor(updatePreview, fields.summary);
                        updatePreview();
                    }
                });
            }
        }

        updatePreview();
    });
})();
