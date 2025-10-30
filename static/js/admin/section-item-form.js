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
        const imageWrapper = root.querySelector('[data-preview-image-wrapper]');
        const imageEl = root.querySelector('[data-preview-image]');

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
            const imageUrl = fields.imageUrl && fields.imageUrl.value.trim();

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

            if (imageWrapper && imageEl) {
                if (imageUrl) {
                    imageEl.src = imageUrl;
                    imageEl.alt = title || defaults.title;
                    imageWrapper.removeAttribute('hidden');
                } else {
                    imageEl.removeAttribute('src');
                    imageWrapper.setAttribute('hidden', '');
                }
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

    function getUploadEndpoint() {
        return window.__orlImageUploadEndpoint || null;
    }

    function ensureImageUploadWrapper(field) {
        const group = field.closest('.form-group') || field.parentElement;
        if (!group) {
            return null;
        }

        group.classList.add('section-item-image-upload-group');

        let wrapper = field.closest('.section-item-image-upload__inner');
        if (!wrapper) {
            wrapper = document.createElement('div');
            wrapper.className = 'section-item-image-upload__inner';

            const parent = field.parentNode;
            if (!parent) {
                return null;
            }

            parent.insertBefore(wrapper, field);
            wrapper.appendChild(field);

            let sibling = wrapper.nextSibling;
            while (sibling) {
                if (
                    sibling.nodeType === Node.ELEMENT_NODE &&
                    (sibling.classList.contains('help-block') ||
                        sibling.classList.contains('form-text') ||
                        sibling.classList.contains('invalid-feedback'))
                ) {
                    const element = sibling;
                    sibling = sibling.nextSibling;
                    wrapper.appendChild(element);
                } else {
                    break;
                }
            }
        }

        let hint = wrapper.querySelector('.section-item-image-upload__hint');
        if (!hint) {
            hint = document.createElement('p');
            hint.className = 'section-item-image-upload__hint';
            hint.innerHTML =
                'Arraste e solte uma imagem aqui, cole com Ctrl+V ou utilize o botão <strong>Escolher arquivo</strong>.' +
                ' Também é possível informar um link externo caso prefira.';
            wrapper.appendChild(hint);
        }

        let feedback = wrapper.querySelector('.section-item-image-upload__feedback');
        if (!feedback) {
            feedback = document.createElement('div');
            feedback.className = 'section-item-image-upload__feedback';
            feedback.setAttribute('aria-live', 'polite');
            wrapper.appendChild(feedback);
        }

        return { group, wrapper, feedback };
    }

    function setupImageUpload(field) {
        if (!field || field.dataset.cardImageUploadBound === '1') {
            return;
        }

        const endpoint = getUploadEndpoint();
        if (!endpoint) {
            return;
        }

        const elements = ensureImageUploadWrapper(field);
        if (!elements) {
            return;
        }

        const { wrapper, feedback } = elements;

        function showFeedback(status, message) {
            if (!feedback) {
                return;
            }

            if (!message) {
                feedback.textContent = '';
                feedback.removeAttribute('data-status');
                return;
            }

            feedback.textContent = message;
            feedback.setAttribute('data-status', status);
        }

        function clearDrag() {
            wrapper.classList.remove('is-dragover');
        }

        function uploadFile(file) {
            if (!file) {
                return;
            }

            showFeedback('', '');
            wrapper.classList.add('is-uploading');

            const formData = new FormData();
            formData.append('upload', file);

            fetch(endpoint, {
                method: 'POST',
                body: formData,
            })
                .then(function (response) {
                    return response
                        .json()
                        .catch(function () {
                            return {};
                        })
                        .then(function (data) {
                            return { ok: response.ok, status: response.status, data: data };
                        });
                })
                .then(function (result) {
                    const data = result && result.data ? result.data : {};

                    if (result && result.ok && data.uploaded === 1 && data.url) {
                        field.value = data.url;
                        field.dispatchEvent(new Event('input', { bubbles: true }));
                        field.dispatchEvent(new Event('change', { bubbles: true }));
                        showFeedback('success', 'Imagem enviada com sucesso.');
                        return;
                    }

                    const message =
                        (data && data.error && data.error.message) ||
                        'Não foi possível enviar a imagem. Tente novamente.';
                    showFeedback('error', message);
                })
                .catch(function () {
                    showFeedback('error', 'Erro de conexão ao enviar a imagem.');
                })
                .finally(function () {
                    wrapper.classList.remove('is-uploading');
                });
        }

        field.addEventListener('paste', function (event) {
            if (!event.clipboardData) {
                return;
            }

            const files = Array.prototype.slice.call(event.clipboardData.files || []);
            if (files.length === 0) {
                return;
            }

            event.preventDefault();
            uploadFile(files[0]);
        });

        wrapper.addEventListener('dragenter', function (event) {
            event.preventDefault();
            wrapper.classList.add('is-dragover');
        });

        wrapper.addEventListener('dragover', function (event) {
            event.preventDefault();
            wrapper.classList.add('is-dragover');
        });

        wrapper.addEventListener('dragleave', function (event) {
            if (event.target === wrapper || !wrapper.contains(event.relatedTarget)) {
                clearDrag();
            }
        });

        wrapper.addEventListener('drop', function (event) {
            event.preventDefault();
            clearDrag();

            const files = event.dataTransfer && event.dataTransfer.files;
            if (files && files.length > 0) {
                uploadFile(files[0]);
            }
        });

        wrapper.addEventListener('dragend', clearDrag);

        field.dataset.cardImageUploadBound = '1';
    }

    ready(function () {
        const root = document.querySelector('[data-section-item-preview]');
        if (!root) {
            return;
        }

        const designer = root.closest('.section-item-designer');
        const fields = {
            title: getField('[name="title"]'),
            summary: getField('[name="summary"]'),
            badge: getField('[name="badge"]'),
            displayDate: getField('[name="display_date"]'),
            linkLabel: getField('[name="link_label"]'),
            linkUrl: getField('[name="link_url"]'),
            imageUrl: designer
                ? designer.querySelector('[data-card-image-input]')
                : getField('[data-card-image-input]'),
        };

        const updatePreview = updatePreviewFactory(root, fields);

        Object.values(fields).forEach(function (field) {
            bindInput(field, updatePreview);
        });

        function bindAllImageInputs() {
            document.querySelectorAll('[data-card-image-input]').forEach(function (input) {
                setupImageUpload(input);
            });
        }

        bindAllImageInputs();

        const observer = new MutationObserver(function () {
            bindAllImageInputs();
        });

        observer.observe(document.body, { childList: true, subtree: true });

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
