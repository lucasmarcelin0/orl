(function () {
    function onCkeditorReady(callback) {
        if (window.CKEDITOR) {
            callback(window.CKEDITOR);
            return;
        }

        document.addEventListener('DOMContentLoaded', function () {
            if (window.CKEDITOR) {
                callback(window.CKEDITOR);
            }
        });
    }

    function getMinHeight(editor) {
        if (editor && editor.element && editor.element.$) {
            const dataset = editor.element.$.dataset || {};
            const attrValue = dataset.ckeditorHeight || editor.element.$.getAttribute('data-ckeditor-height');
            const parsed = parseInt(attrValue, 10);
            if (!Number.isNaN(parsed)) {
                return parsed;
            }
        }

        const configHeight = parseInt(editor && editor.config && editor.config.height, 10);
        if (!Number.isNaN(configHeight)) {
            return configHeight;
        }

        return 200;
    }

    function computeContentHeight(editor, minHeight) {
        if (!editor) {
            return minHeight;
        }

        try {
            const body = editor.document && editor.document.getBody ? editor.document.getBody() : null;
            if (!body) {
                return minHeight;
            }

            const scrollHeight = body.$ ? body.$.scrollHeight : 0;
            const paddingTop = parseInt(body.getComputedStyle('padding-top') || '0', 10) || 0;
            const paddingBottom = parseInt(body.getComputedStyle('padding-bottom') || '0', 10) || 0;
            const borders =
                (parseInt(body.getComputedStyle('border-top-width') || '0', 10) || 0) +
                (parseInt(body.getComputedStyle('border-bottom-width') || '0', 10) || 0);

            const extra = paddingTop + paddingBottom + borders + 24; // breathing space
            return Math.max(scrollHeight + extra, minHeight);
        } catch (error) {
            return minHeight;
        }
    }

    function refreshHeight(editor) {
        if (!editor) {
            return;
        }

        const minHeight = getMinHeight(editor);
        const desiredHeight = computeContentHeight(editor, minHeight);
        editor.resize(null, desiredHeight, true);
    }

    function suppressVersionWarning(editor) {
        const hideNotification = function (notification) {
            if (!notification) {
                return;
            }

            const message = (notification.message || '').toLowerCase();
            if (message.includes('not secure') || message.includes('consider upgrading')) {
                notification.hide();
            }
        };

        editor.on('notificationShow', function (event) {
            hideNotification(event && event.data && event.data.notification);
        });

        // Hide notifications that might have already been displayed.
        if (editor._.notificationArea && Array.isArray(editor._.notificationArea.notifications)) {
            editor._.notificationArea.notifications.forEach(hideNotification);
        }

        const warningElement = editor.container && editor.container.findOne('.cke_notification');
        if (warningElement) {
            warningElement.hide();
        }
    }

    function bindAutoResize(editor) {
        if (!editor) {
            return;
        }

        const update = function () {
            refreshHeight(editor);
        };

        editor.on('dataReady', update);
        editor.on('change', update);
        editor.on('afterPaste', update);
        editor.on('mode', function () {
            if (editor.mode === 'wysiwyg') {
                update();
            }
        });

        // Initial adjustment for already available content.
        update();
    }

    onCkeditorReady(function (CKEDITOR) {
        CKEDITOR.on('instanceReady', function (event) {
            const editor = event.editor;
            suppressVersionWarning(editor);
            bindAutoResize(editor);
        });
    });
})();
