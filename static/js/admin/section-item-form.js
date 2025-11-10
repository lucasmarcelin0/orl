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

    var IMAGE_SCALE_MIN = 0.5;
    var IMAGE_SCALE_MAX = 2;
    var IMAGE_ROTATION_MIN = -180;
    var IMAGE_ROTATION_MAX = 180;

    function clamp(value, min, max) {
        if (Number.isNaN(value)) {
            return value;
        }
        if (value < min) {
            return min;
        }
        if (value > max) {
            return max;
        }
        return value;
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
        const editor = window.CKEDITOR && textarea.id ? window.CKEDITOR.instances[textarea.id] : null;

        if (editor) {
            editor.focus();
            return;
        }

        focusField(textarea);
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
        const imageControls = root.querySelector('[data-preview-image-controls]');
        const scaleControl = root.querySelector('[data-preview-image-scale-control]');
        const rotationControl = root.querySelector('[data-preview-image-rotation-control]');
        const scaleValueEl = root.querySelector('[data-preview-image-scale-value]');
        const rotationValueEl = root.querySelector('[data-preview-image-rotation-value]');
        const resetControl = root.querySelector('[data-preview-image-reset]');

        const defaults = {
            title: 'Título do cartão',
            summary:
                '<p>Utilize o campo “Resumo” para adicionar o conteúdo que aparecerá no site.</p>',
            link: 'Adicionar link',
            badge: 'Adicionar selo',
            date: 'Definir data',
        };

        function parseScale() {
            const value = fields.imageScale ? parseFloat(fields.imageScale.value) : NaN;
            if (Number.isNaN(value)) {
                return 1;
            }
            return clamp(value, IMAGE_SCALE_MIN, IMAGE_SCALE_MAX);
        }

        function parseRotation() {
            const value = fields.imageRotation ? parseFloat(fields.imageRotation.value) : NaN;
            if (Number.isNaN(value)) {
                return 0;
            }
            return clamp(value, IMAGE_ROTATION_MIN, IMAGE_ROTATION_MAX);
        }

        function formatScale(scale) {
            return Math.round(scale * 100);
        }

        function syncImageControls(scale, rotation, hasImage) {
            if (!imageControls) {
                return;
            }

            if (hasImage) {
                imageControls.removeAttribute('hidden');
            } else {
                imageControls.setAttribute('hidden', '');
            }

            if (scaleControl) {
                scaleControl.value = String(formatScale(scale));
                scaleControl.disabled = !hasImage;
            }
            if (scaleValueEl) {
                scaleValueEl.textContent = formatScale(scale) + '%';
            }

            if (rotationControl) {
                rotationControl.value = String(Math.round(rotation));
                rotationControl.disabled = !hasImage;
            }
            if (rotationValueEl) {
                rotationValueEl.textContent = Math.round(rotation) + '°';
            }

            if (resetControl) {
                resetControl.disabled = !hasImage;
            }
        }

        return function updatePreview() {
            const title = fields.title && fields.title.value.trim();
            const badge = fields.badge && fields.badge.value.trim();
            const date = fields.displayDate && fields.displayDate.value.trim();
            const linkLabel = fields.linkLabel && fields.linkLabel.value.trim();
            const linkUrl = fields.linkUrl && fields.linkUrl.value.trim();
            const imageUrl = fields.imageUrl && fields.imageUrl.value.trim();
            const scale = parseScale();
            const rotation = parseRotation();
            const hasImage = Boolean(imageUrl);

            if (fields.imageScale) {
                const normalizedScale = scale.toFixed(2);
                if (fields.imageScale.value !== normalizedScale) {
                    fields.imageScale.value = normalizedScale;
                }
            }

            if (fields.imageRotation) {
                const normalizedRotation = String(Math.round(rotation));
                if (fields.imageRotation.value !== normalizedRotation) {
                    fields.imageRotation.value = normalizedRotation;
                }
            }

            if (titleEl) {
                titleEl.textContent = title || defaults.title;
                titleEl.dataset.placeholder = title ? 'false' : 'true';
            }

            if (summaryEl) {
                const editor = window.CKEDITOR && fields.summary && fields.summary.id
                    ? window.CKEDITOR.instances[fields.summary.id]
                    : null;

                const rawSummaryValue = editor ? editor.getData() : fields.summary?.value || '';
                const decodedSummary = decodeHtml(rawSummaryValue);
                const content = sanitizeHtml(decodedSummary).trim();
                summaryEl.innerHTML = content || defaults.summary;
                summaryEl.dataset.placeholder = content ? 'false' : 'true';
            }

            if (imageWrapper && imageEl) {
                if (imageUrl) {
                    imageEl.src = imageUrl;
                    imageEl.alt = title || defaults.title;
                    imageEl.removeAttribute('hidden');
                    imageWrapper.classList.add('has-image');
                    if (imagePlaceholder) {
                        imagePlaceholder.setAttribute('hidden', '');
                    }
                    imageEl.style.transform = 'scale(' + scale + ') rotate(' + rotation + 'deg)';
                } else {
                    imageEl.removeAttribute('src');
                    imageEl.setAttribute('hidden', '');
                    imageWrapper.classList.remove('has-image');
                    if (imagePlaceholder) {
                        imagePlaceholder.removeAttribute('hidden');
                    }
                    imageEl.style.transform = '';
                }
            }

            if (badgeEl) {
                if (badge) {
                    badgeEl.textContent = badge;
                    badgeEl.dataset.placeholder = 'false';
                } else {
                    badgeEl.textContent = defaults.badge;
                    badgeEl.dataset.placeholder = 'true';
                }
            }

            if (dateEl) {
                if (date) {
                    dateEl.textContent = date;
                    dateEl.dataset.placeholder = 'false';
                } else {
                    dateEl.textContent = defaults.date;
                    dateEl.dataset.placeholder = 'true';
                }
            }

            if (linkEl && linkLabelEl) {
                if (linkLabel) {
                    linkLabelEl.textContent = linkLabel;
                    linkEl.setAttribute('href', normalizeUrl(linkUrl));
                    linkEl.dataset.placeholder = 'false';
                } else {
                    linkLabelEl.textContent = defaults.link;
                    linkEl.setAttribute('href', '#');
                    linkEl.dataset.placeholder = 'true';
                }
            }

            syncImageControls(scale, rotation, hasImage);
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
            imageScale: getField('[name="image_scale"]'),
            imageRotation: getField('[name="image_rotation"]'),
        };

        if (fields.imageScale && !fields.imageScale.value) {
            fields.imageScale.value = '1.00';
        }
        if (fields.imageRotation && !fields.imageRotation.value) {
            fields.imageRotation.value = '0';
        }

        const updatePreview = updatePreviewFactory(root, fields);

        Object.values(fields).forEach(function (field) {
            bindInput(field, updatePreview);
        });

        const scaleControl = root.querySelector('[data-preview-image-scale-control]');
        const rotationControl = root.querySelector('[data-preview-image-rotation-control]');
        const resetControl = root.querySelector('[data-preview-image-reset]');

        if (scaleControl && fields.imageScale) {
            scaleControl.addEventListener('input', function (event) {
                const target = event.target;
                const percent = parseInt(target.value, 10);
                let normalized = percent / 100;
                if (Number.isNaN(normalized)) {
                    normalized = 1;
                }
                normalized = clamp(normalized, IMAGE_SCALE_MIN, IMAGE_SCALE_MAX);
                const formatted = normalized.toFixed(2);
                if (fields.imageScale.value !== formatted) {
                    fields.imageScale.value = formatted;
                }
                updatePreview();
            });
        }

        if (rotationControl && fields.imageRotation) {
            rotationControl.addEventListener('input', function (event) {
                const target = event.target;
                const degrees = parseInt(target.value, 10);
                let normalized = Number.isNaN(degrees) ? 0 : degrees;
                normalized = clamp(normalized, IMAGE_ROTATION_MIN, IMAGE_ROTATION_MAX);
                const formatted = String(Math.round(normalized));
                if (fields.imageRotation.value !== formatted) {
                    fields.imageRotation.value = formatted;
                }
                updatePreview();
            });
        }

        if (resetControl && fields.imageScale && fields.imageRotation) {
            resetControl.addEventListener('click', function (event) {
                event.preventDefault();
                const defaultScale = '1.00';
                const defaultRotation = '0';
                let shouldUpdate = false;

                if (fields.imageScale.value !== defaultScale) {
                    fields.imageScale.value = defaultScale;
                    shouldUpdate = true;
                }

                if (fields.imageRotation.value !== defaultRotation) {
                    fields.imageRotation.value = defaultRotation;
                    shouldUpdate = true;
                }

                if (shouldUpdate) {
                    updatePreview();
                }
            });
        }

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
