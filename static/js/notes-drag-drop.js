// Drag and Drop functionality for notes
(function () {
    let draggedElement = null;
    let draggedIndex = null;

    function setupDragAndDrop() {
        const noteBoard = document.getElementById('noteBoard');
        if (!noteBoard) return;

        const noteRows = noteBoard.querySelectorAll('.note-row');

        noteRows.forEach((row, index) => {
            row.addEventListener('dragstart', (e) => {
                draggedElement = row;
                draggedIndex = index;
                row.classList.add('dragging');
                e.dataTransfer.effectAllowed = 'move';
                e.dataTransfer.setData('text/html', row.innerHTML);
            });

            row.addEventListener('dragend', (e) => {
                row.classList.remove('dragging');
                // Remove all drag-over classes
                noteRows.forEach(r => r.classList.remove('drag-over'));
                draggedElement = null;
                draggedIndex = null;
            });

            row.addEventListener('dragover', (e) => {
                e.preventDefault();
                e.dataTransfer.dropEffect = 'move';

                if (draggedElement && draggedElement !== row) {
                    row.classList.add('drag-over');
                }
            });

            row.addEventListener('dragleave', (e) => {
                row.classList.remove('drag-over');
            });

            row.addEventListener('drop', (e) => {
                e.preventDefault();
                row.classList.remove('drag-over');

                if (draggedElement && draggedElement !== row) {
                    const targetIndex = index;

                    // Reorder DOM elements
                    if (draggedIndex < targetIndex) {
                        row.parentNode.insertBefore(draggedElement, row.nextSibling);
                    } else {
                        row.parentNode.insertBefore(draggedElement, row);
                    }
                }
            });
        });
    }

    // Setup drag and drop when notes are rendered
    // We'll use a MutationObserver to detect when notes are added to the DOM
    const noteBoard = document.getElementById('noteBoard');
    if (noteBoard) {
        const observer = new MutationObserver(() => {
            setupDragAndDrop();
        });

        observer.observe(noteBoard, {
            childList: true,
            subtree: true
        });

        // Initial setup
        setupDragAndDrop();
    }
})();
