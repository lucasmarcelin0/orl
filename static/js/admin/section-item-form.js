(function () {
    const PREVIEW_DEFAULTS = {
        title: 'Título do cartão',
        summary: '<p>Utilize o campo “Resumo” para adicionar o conteúdo que aparecerá no site.</p>',
        link: 'Adicionar link',
        badge: 'Adicionar selo',
        date: 'Definir data',
    };

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

    function decodeHtml(html) {
        if (!html) {
            return '';
        }

        const textarea = document.createElement('textarea');
        textarea.innerHTML = html;
        return textarea.value;
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

    function focusField(field) {
        if (!field) {
            return;
        }

        if (field.tagName === 'INPUT' || field.tagName === 'SELECT' || field.tagName === 'TEXTAREA') {
            field.focus({ preventScroll: false });
            if (typeof field.select === 'function') {
                field.select();
            }
            return;
        }

        field.focus({ preventScroll: false });
    }

    function focusSummaryField(fields) {
        if (!fields.summary) {
            return;
        }

        const textarea = fields.summary;
        const group = textarea.closest('.form-group');
        if (group) {
            group.classList.add('section-item-summary-group--highlight');
            window.setTimeout(function () {
                group.classList.remove('section-item-summary-group--highlight');
            }, 2000);
        }

        const editor = window.CKEDITOR && textarea.id ? window.CKEDITOR.instances[textarea.id] : null;

        if (editor) {
            const container = editor.container && editor.container.$ ? editor.container.$ : null;
            if (container && typeof container.scrollIntoView === 'function') {
                try {
                    container.scrollIntoView({ behavior: 'smooth', block: 'center' });
                } catch (error) {
                    container.scrollIntoView(true);
                }
            }
            editor.focus();
            return;
        }

        focusField(textarea);
        if (typeof textarea.scrollIntoView === 'function') {
            try {
                textarea.scrollIntoView({ behavior: 'smooth', block: 'center' });
            } catch (error) {
                textarea.scrollIntoView(true);
            }
        }
    }

    function bindPreviewInteractions(root, fields) {
        function getImageUploadButton() {
            const designerRoot = root.closest('.section-item-designer');
            if (designerRoot) {
                const button = designerRoot.querySelector('[data-card-image-upload-button]');
                if (button) {
                    return button;
                }
            }
            return document.querySelector('[data-card-image-upload-button]');
        }

        function handleAction(action) {
            if (!action) {
                return;
            }

            switch (action) {
                case 'title':
                    focusField(fields.title);
                    break;
                case 'summary':
                    focusSummaryField(fields);
                    break;
                case 'badge':
                    focusField(fields.badge);
                    break;
                case 'date':
                    focusField(fields.displayDate);
                    break;
                case 'link':
                    focusField(fields.linkLabel);
                    break;
                case 'image': {
                    const button = getImageUploadButton();
                    if (button) {
                        button.click();
                        break;
                    }
                    focusField(fields.imageUrl);
                    break;
                }
                default:
                    break;
            }
        }

        function getActionTarget(element) {
            if (!element) {
                return null;
            }

            if (element.closest('[data-preview-editable]')) {
                return null;
            }

            return element.closest('[data-preview-trigger]');
        }

        root.addEventListener('click', function (event) {
            const target = getActionTarget(event.target);
            if (!target) {
                return;
            }

            event.preventDefault();
            handleAction(target.dataset.previewTrigger);
        });

        root.addEventListener('keydown', function (event) {
            if (event.key !== 'Enter' && event.key !== ' ' && event.key !== 'Spacebar' && event.key !== 'Space') {
                return;
            }

            const target = getActionTarget(event.target);
            if (!target) {
                return;
            }

            event.preventDefault();
            handleAction(target.dataset.previewTrigger);
        });
    }

    function setEditableContent(element, value, placeholder, options) {
        if (!element) {
            return;
        }

        const config = options || {};
        const isHtml = !!config.isHtml;
        const hasValue = !!value;
        const displayValue = hasValue ? value : placeholder;
        const isActive = document.activeElement === element;
        const isSyncing = element.dataset && element.dataset.syncing === '1';

        if (!isActive || isSyncing) {
            if (isHtml) {
                if (element.innerHTML !== displayValue) {
                    element.innerHTML = displayValue;
                }
            } else if (element.textContent !== displayValue) {
                element.textContent = displayValue;
            }
        }

        element.dataset.placeholder = hasValue ? 'false' : 'true';

        if (isSyncing) {
            delete element.dataset.syncing;
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
        const imagePlaceholder = root.querySelector('[data-preview-image-empty]');

        return function updatePreview() {
            const title = fields.title && fields.title.value.trim();
            const badge = fields.badge && fields.badge.value.trim();
            const date = fields.displayDate && fields.displayDate.value.trim();
            const linkLabel = fields.linkLabel && fields.linkLabel.value.trim();
            const linkUrl = fields.linkUrl && fields.linkUrl.value.trim();
            const imageUrl = fields.imageUrl && fields.imageUrl.value.trim();

            setEditableContent(titleEl, title, PREVIEW_DEFAULTS.title);

            if (summaryEl) {
                const editor = window.CKEDITOR && fields.summary && fields.summary.id
                    ? window.CKEDITOR.instances[fields.summary.id]
                    : null;

                const rawSummaryValue = editor ? editor.getData() : fields.summary?.value || '';
                const decodedSummary = decodeHtml(rawSummaryValue);
                const content = sanitizeHtml(decodedSummary).trim();
                setEditableContent(summaryEl, content, PREVIEW_DEFAULTS.summary, { isHtml: true });
            }

            if (imageWrapper && imageEl) {
                if (imageUrl) {
                    imageEl.src = imageUrl;
                    imageEl.alt = title || PREVIEW_DEFAULTS.title;
                    imageEl.removeAttribute('hidden');
                    imageWrapper.classList.add('has-image');
                    if (imagePlaceholder) {
                        imagePlaceholder.setAttribute('hidden', '');
                    }
                } else {
                    imageEl.removeAttribute('src');
                    imageEl.setAttribute('hidden', '');
                    imageWrapper.classList.remove('has-image');
                    if (imagePlaceholder) {
                        imagePlaceholder.removeAttribute('hidden');
                    }
                }
            }

            setEditableContent(badgeEl, badge, PREVIEW_DEFAULTS.badge);
            setEditableContent(dateEl, date, PREVIEW_DEFAULTS.date);

            if (linkEl && linkLabelEl) {
                if (linkLabel) {
                    setEditableContent(linkLabelEl, linkLabel, PREVIEW_DEFAULTS.link);
                    linkEl.setAttribute('href', normalizeUrl(linkUrl));
                    linkEl.dataset.placeholder = 'false';
                } else {
                    setEditableContent(linkLabelEl, '', PREVIEW_DEFAULTS.link);
                    linkEl.setAttribute('href', '#');
                    linkEl.dataset.placeholder = 'true';
                }
            }
        };
    }

    function bindEditablePlaceholder(element, options) {
        if (!element) {
            return;
        }

        const config = options || {};
        const isHtml = !!config.isHtml;

        element.addEventListener('focus', function () {
            if (element.dataset.placeholder === 'true') {
                if (isHtml) {
                    element.innerHTML = '';
                } else {
                    element.textContent = '';
                }
                element.dataset.placeholder = 'false';
            }
        });
    }

    function bindPreviewEditors(root, fields, updatePreview) {
        const configs = [
            {
                element: root.querySelector('[data-preview-title]'),
                field: fields.title,
                placeholder: PREVIEW_DEFAULTS.title,
                multiline: false,
            },
            {
                element: root.querySelector('[data-preview-summary]'),
                field: fields.summary,
                placeholder: PREVIEW_DEFAULTS.summary,
                multiline: true,
                isHtml: true,
            },
            {
                element: root.querySelector('[data-preview-badge]'),
                field: fields.badge,
                placeholder: PREVIEW_DEFAULTS.badge,
                multiline: false,
            },
            {
                element: root.querySelector('[data-preview-date]'),
                field: fields.displayDate,
                placeholder: PREVIEW_DEFAULTS.date,
                multiline: false,
            },
            {
                element: root.querySelector('[data-preview-link-label]'),
                field: fields.linkLabel,
                placeholder: PREVIEW_DEFAULTS.link,
                multiline: false,
            },
        ];

        configs.forEach(function (config) {
            const element = config.element;
            const field = config.field;

            if (!element || !field) {
                return;
            }

            bindEditablePlaceholder(element, { isHtml: config.isHtml });

            element.addEventListener('keydown', function (event) {
                if (!config.multiline && (event.key === 'Enter' || event.key === 'Return')) {
                    event.preventDefault();
                    element.blur();
                }
            });

            function normaliseValue(value) {
                if (!value) {
                    return '';
                }

                const cleaned = value.replace(/\u00a0/g, ' ');
                if (config.isHtml) {
                    return sanitizeHtml(cleaned).trim();
                }

                if (config.multiline) {
                    return cleaned.trim();
                }

                return cleaned.replace(/\s+/g, ' ').trim();
            }

            function syncFieldFromPreview() {
                if (config.isHtml) {
                    const newValue = normaliseValue(element.innerHTML || '');
                    const editor =
                        window.CKEDITOR && field.id && window.CKEDITOR.instances[field.id]
                            ? window.CKEDITOR.instances[field.id]
                            : null;

                    if (editor) {
                        const currentValue = sanitizeHtml(editor.getData() || '').trim();
                        if (currentValue !== newValue) {
                            element.dataset.syncing = '1';
                            editor.setData(newValue);
                        } else {
                            element.dataset.syncing = '1';
                        }
                        updatePreview();
                        return;
                    }

                    const currentValue = sanitizeHtml(field.value || '').trim();
                    if (currentValue !== newValue) {
                        field.value = newValue;
                        field.dispatchEvent(new Event('input', { bubbles: true }));
                        field.dispatchEvent(new Event('change', { bubbles: true }));
                    } else {
                        field.dispatchEvent(new Event('input', { bubbles: true }));
                    }
                    return;
                }

                const newValue = normaliseValue(element.textContent || '');
                const currentValue = field.value || '';

                if (currentValue !== newValue) {
                    field.value = newValue;
                    field.dispatchEvent(new Event('input', { bubbles: true }));
                    field.dispatchEvent(new Event('change', { bubbles: true }));
                } else {
                    field.dispatchEvent(new Event('input', { bubbles: true }));
                }
            }

            element.addEventListener('input', function () {
                syncFieldFromPreview();
            });

            element.addEventListener('blur', function () {
                syncFieldFromPreview();
                if (config.isHtml) {
                    const textValue = (element.textContent || '').trim();
                    if (!textValue) {
                        element.dataset.placeholder = 'true';
                        element.innerHTML = '';
                    }
                } else if (!element.textContent) {
                    element.dataset.placeholder = 'true';
                }
                updatePreview();
            });
        });
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

    function getUploadEndpoint(field) {
        if (field && field.dataset && field.dataset.cardImageEndpoint) {
            return field.dataset.cardImageEndpoint;
        }
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

        const elements = ensureImageUploadWrapper(field);
        if (!elements) {
            field.dataset.cardImageUploadBound = '1';
            return;
        }

        const { wrapper, feedback } = elements;

        const endpoint = getUploadEndpoint(field);
        if (!endpoint) {
            if (feedback) {
                feedback.textContent =
                    'Envio direto de imagens indisponível. Informe um endereço completo da imagem ou contate o suporte para habilitar o recurso.';
                feedback.setAttribute('data-status', 'error');
            }
            field.dataset.cardImageUploadBound = '1';
            return;
        }

        let actions = wrapper.querySelector('.section-item-image-upload__actions');
        if (!actions) {
            actions = document.createElement('div');
            actions.className = 'section-item-image-upload__actions';

            const hint = wrapper.querySelector('.section-item-image-upload__hint');
            if (hint) {
                wrapper.insertBefore(actions, hint);
            } else if (feedback) {
                wrapper.insertBefore(actions, feedback);
            } else {
                wrapper.appendChild(actions);
            }
        }

        let button = actions.querySelector('[data-card-image-upload-button]');
        if (!button) {
            button = document.createElement('button');
            button.type = 'button';
            button.className = 'btn btn-primary btn-sm';
            button.textContent = 'Escolher arquivo';
            button.setAttribute('data-card-image-upload-button', '1');
            actions.appendChild(button);
        }

        let orText = actions.querySelector('.section-item-image-upload__actions-text');
        if (!orText) {
            orText = document.createElement('span');
            orText.className = 'section-item-image-upload__actions-text';
            orText.textContent = 'ou informe um link externo abaixo';
            actions.appendChild(orText);
        }

        let fileInput = wrapper.querySelector('[data-card-image-file-input]');
        if (!fileInput) {
            fileInput = document.createElement('input');
            fileInput.type = 'file';
            fileInput.accept = 'image/*';
            fileInput.setAttribute('data-card-image-file-input', '1');
            fileInput.setAttribute('hidden', '');
            wrapper.appendChild(fileInput);
        }

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

        if (button && fileInput) {
            button.addEventListener('click', function (event) {
                event.preventDefault();
                fileInput.click();
            });

            fileInput.addEventListener('change', function () {
                const file = fileInput.files && fileInput.files[0];
                if (file) {
                    uploadFile(file);
                }
                fileInput.value = '';
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

        bindPreviewEditors(root, fields, updatePreview);

        function bindAllImageInputs() {
            document.querySelectorAll('[data-card-image-input]').forEach(function (input) {
                setupImageUpload(input);
            });
        }

        bindAllImageInputs();

        bindPreviewInteractions(root, fields);

        function setupDocumentsInlineLayout() {
            const inlineRoot = document.getElementById('documents');
            if (!inlineRoot || inlineRoot.dataset.sectionItemDocumentsBound === '1') {
                return;
            }

            const fieldset = inlineRoot.closest('fieldset');
            if (!fieldset) {
                return;
            }

            let wrapper = fieldset.querySelector('[data-section-item-documents]');
            if (!wrapper) {
                wrapper = document.createElement('div');
                wrapper.className = 'section-item-documents';
                wrapper.setAttribute('data-section-item-documents', '1');

                const heading = fieldset.querySelector('h3, legend');
                if (heading) {
                    heading.insertAdjacentElement('afterend', wrapper);
                } else {
                    fieldset.appendChild(wrapper);
                }
            }

            const formGroup = inlineRoot.closest('.form-group');
            const target = formGroup || inlineRoot;

            wrapper.appendChild(target);
            target.classList.add('section-item-documents__group');
            inlineRoot.classList.add('section-item-documents__inline');
            inlineRoot.dataset.sectionItemDocumentsBound = '1';
        }

        setupDocumentsInlineLayout();

        const observer = new MutationObserver(function () {
            bindAllImageInputs();
            setupDocumentsInlineLayout();
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
