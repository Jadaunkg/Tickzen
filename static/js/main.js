function initializeReportDisplay(reportUrlData) {
    const iframe = document.getElementById('report-iframe');
    const loadingMessage = document.querySelector('.loading-message');
    const reportArea = document.getElementById('report-content-area');
    const reportUrl = reportUrlData; // reportUrlData is passed from the template

    // Ensure necessary elements are present on the page
    if (!iframe || !reportArea) {
        // console.log("Report display iframe or content area not found. Skipping iframe initialization.");
        return;
    }
    // loadingMessage is optional, so we'll check for its existence before using
    if (loadingMessage) {
        // console.log("Loading message element found.");
    }


    // --- Start of functions taken from your provided report_display.html script ---
    let resizeTimer; // This was in your script, kept for consistency if used by your logic

    function resizePlotlyPlots() {
        try {
            // Check if iframe and its contentWindow are accessible and Plotly exists
            if (!iframe.contentWindow || !iframe.contentWindow.document || !iframe.contentWindow.Plotly) {
                // console.warn("Iframe content or Plotly not ready for Plotly resize.");
                return;
            }
            const plotlyInstance = iframe.contentWindow.Plotly;
            if (plotlyInstance && typeof plotlyInstance.Plots !== 'undefined' && typeof plotlyInstance.Plots.resize === 'function') {
                const plotDivs = iframe.contentWindow.document.querySelectorAll('.plotly-graph-div');
                if (plotDivs.length > 0) {
                    plotDivs.forEach(div => {
                        try {
                            if (div.offsetParent !== null) { // Check if element is visible
                                plotlyInstance.Plots.resize(div);
                            }
                        } catch (resizeError) {
                            // console.error('Error resizing individual plot div:', resizeError, div.id);
                        }
                    });
                }
            }
        } catch (error) {
            if (error.name !== 'SecurityError') {
                 console.error('Error accessing iframe content or Plotly for resize:', error);
            }
        }
    }

    function adjustIframeHeight() {
         try {
            if (!iframe.contentWindow || !iframe.contentWindow.document || !iframe.contentWindow.document.body) {
                console.warn("Iframe content not fully accessible yet for height adjustment.");
                iframe.style.height = '100vh'; // Fallback
                return;
            }
            const iframeDoc = iframe.contentWindow.document;
            const contentHeight = iframeDoc.body.scrollHeight;

            if (contentHeight > 0) {
                iframe.style.height = contentHeight + 'px';
            } else {
                iframe.style.height = '100vh';
            }
         } catch(error) {
             if (error.name !== 'SecurityError') {
                 console.warn('Could not adjust iframe height:', error);
             }
             iframe.style.height = '120vh'; // Fallback height on error
         }
    }
    // --- End of functions taken from your provided report_display.html script ---


    if (reportUrl && reportUrl !== 'None' && reportUrl.trim() !== '' && reportUrl.trim() !== '#') {
        iframe.src = reportUrl;

        iframe.onload = function() {
            if (loadingMessage) { // Check if element exists
                loadingMessage.style.display = 'none';
            }
            iframe.style.visibility = 'visible';

            let attempts = 0;
            const maxAttempts = 5; // From your script
            function attemptAdjustments() {
                // Check if iframe contentWindow and body are ready before proceeding
                if (!iframe.contentWindow || !iframe.contentWindow.document || !iframe.contentWindow.document.body || iframe.contentWindow.document.readyState !== 'complete') {
                    if (attempts < maxAttempts) {
                        attempts++;
                        setTimeout(attemptAdjustments, 250 + (attempts * 50)); // Give a bit more time
                        return;
                    } else {
                        console.warn("Max attempts for iframe readiness reached. Trying final adjustment.");
                        // Proceed with adjustment even if not "fully complete" according to readyState,
                        // as scrollHeight might still be measurable.
                    }
                }

                resizePlotlyPlots();
                adjustIframeHeight();
                
                // This part of your logic for retrying if clientHeight is small:
                attempts++; // Ensure attempts is incremented for this path as well
                if (iframe.clientHeight < 200 && attempts < maxAttempts) {
                    setTimeout(attemptAdjustments, 300); 
                } else {
                    try {
                       let rafScheduled = false;
                       const debouncedResize = () => {
                           if (!rafScheduled) {
                               rafScheduled = true;
                               requestAnimationFrame(() => {
                                   resizePlotlyPlots();
                                   adjustIframeHeight();
                                   rafScheduled = false;
                               });
                           }
                       };
                       if(iframe.contentWindow) { // Check again before adding listener
                           iframe.contentWindow.addEventListener('resize', debouncedResize);
                       }
                       window.addEventListener('resize', debouncedResize);
                    } catch(e) {
                       if (e.name !== 'SecurityError') { 
                            console.warn("Could not add resize listener to iframe window.", e);
                       }
                    }
                }
            }
            // Start first attempt after a short delay for initial content rendering in iframe
            setTimeout(attemptAdjustments, 250); 
        };

        iframe.onerror = function() {
            if (reportArea) { // Check if element exists
                reportArea.innerHTML = '<p class="error-message">Error: Failed to load report content. The file might be missing or inaccessible.</p>';
            }
            if (loadingMessage) { // Check if element exists
                loading_message.style.display = 'none';
            }
        };
    } else {
        if (reportArea) { // Check if element exists
            reportArea.innerHTML = '<p class="error-message">Error: Invalid or missing report URL.</p>';
        }
        if (loadingMessage) { // Check if element exists
            loadingMessage.style.display = 'none';
        }
    }
}


// (Ensure this is the only top-level DOMContentLoaded listener in main.js)
document.addEventListener('DOMContentLoaded', function() {
    // Your existing console.log from main.js or a new one:
    console.log("Main JavaScript Initializing (with report display logic)..."); 

    // --- START: Conditional initialization for report display iframe ---
    // This part checks if we are on the report_display.html page and calls the new function.
    const reportIframeElement = document.getElementById('report-iframe');
    if (reportIframeElement && reportIframeElement.hasAttribute('data-report-url')) {
        const reportUrlForDisplay = reportIframeElement.getAttribute('data-report-url');
        if (typeof initializeReportDisplay === 'function') {
            initializeReportDisplay(reportUrlForDisplay);
        } else {
            console.error("initializeReportDisplay function is not defined. Check main.js structure.");
        }
    }



    /**
     * Adds a set of input fields for a new writer to the specified container.
     * @param {string} containerId - The ID of the div element to append writer fields to.
     * @param {object|null} existingAuthor - Optional. Data for an existing author to pre-fill fields.
     * @param {string} formType - 'add' or 'edit', used to prefix IDs for uniqueness.
     */
    function addWriterFields(containerId, existingAuthor = null, formType = 'add') {
        const container = document.getElementById(containerId);
        if (!container) {
            console.error(`Writer fields container with ID '${containerId}' not found.`);
            return;
        }

        const writerCount = container.querySelectorAll('.writer-entry').length;
        const writerEntry = document.createElement('div');
        writerEntry.classList.add('writer-entry');
        
        const idPrefix = formType + '_'; 

        const authorId = (existingAuthor && existingAuthor.id) ? existingAuthor.id : `new_${Date.now()}_${writerCount}`;
        const wpUsername = (existingAuthor && existingAuthor.wp_username) ? existingAuthor.wp_username : '';
        const wpUserId = (existingAuthor && existingAuthor.wp_user_id) ? existingAuthor.wp_user_id : '';
        const appPassword = (formType === 'add' && existingAuthor && existingAuthor.app_password) ? existingAuthor.app_password : '';


        writerEntry.innerHTML = `
            <h4>Writer ${writerCount + 1} <button type="button" class="remove-writer-btn" title="Remove this writer"><i class="fas fa-trash-alt"></i> Remove</button></h4>
            <input type="hidden" name="author_id_${writerCount}" value="${authorId}">
            <div class="form-group">
                <label for="${idPrefix}author_wp_username_${writerCount}">WordPress Username:</label>
                <input type="text" id="${idPrefix}author_wp_username_${writerCount}" name="author_wp_username_${writerCount}" class="form-control" value="${wpUsername}" required placeholder="WP Username">
            </div>
            <div class="form-group">
                <label for="${idPrefix}author_wp_user_id_${writerCount}">WordPress User ID:</label>
                <input type="text" id="${idPrefix}author_wp_user_id_${writerCount}" name="author_wp_user_id_${writerCount}" class="form-control" value="${wpUserId}" required placeholder="e.g., 3 (See guidelines)">
            </div>
            <div class="form-group">
                <label for="${idPrefix}author_app_password_${writerCount}">WordPress Application Password:</label>
                <input type="password" id="${idPrefix}author_app_password_${writerCount}" name="author_app_password_${writerCount}" class="form-control" value="${appPassword}" required placeholder="Enter Application Password">
                ${formType === 'edit' ? '<small class="form-text">Leave blank to keep existing password, or enter new to update.</small>' : ''}
            </div>
        `;
        container.appendChild(writerEntry);

        const newRemoveButton = writerEntry.querySelector('.remove-writer-btn');
        if (newRemoveButton) {
            newRemoveButton.addEventListener('click', function() {
                removeWriter(this);
            });
        }
    }

    function removeWriter(button) {
        const writerEntry = button.closest('.writer-entry');
        if (writerEntry) {
            const container = writerEntry.parentElement;
            writerEntry.remove();
            if (container) { 
                const remainingEntries = container.querySelectorAll('.writer-entry');
                remainingEntries.forEach((entry, index) => {
                    const heading = entry.querySelector('h4');
                    if (heading) {
                        const removeBtnHTML = heading.querySelector('.remove-writer-btn') ? heading.querySelector('.remove-writer-btn').outerHTML : '';
                        heading.innerHTML = `Writer ${index + 1} ${removeBtnHTML}`;
                    }
                });
            }
        }
    }

    function initializeAuthorManagement(containerId, addButtonId, existingAuthorsData = [], formType = 'add') {
        const addAuthorBtn = document.getElementById(addButtonId);
        const container = document.getElementById(containerId);

        if (!addAuthorBtn || !container) {
            return;
        }
        container.querySelectorAll('.writer-entry').forEach(entry => entry.remove());

        if (existingAuthorsData && existingAuthorsData.length > 0) {
            existingAuthorsData.forEach(author => addWriterFields(containerId, author, formType));
        } else {
            if (formType === 'add') { 
                 addWriterFields(containerId, null, formType);
            }
        }

        addAuthorBtn.onclick = function() {
            addWriterFields(containerId, null, formType);
        };
    }
    
    function setupReportSectionControls(formPrefix) { 
        const selectAllBtn = document.getElementById('selectAllSections' + formPrefix);
        const unselectAllBtn = document.getElementById('unselectAllSections' + formPrefix);
        const checkboxesContainer = document.getElementById('reportSections' + formPrefix + 'Container');

        if(selectAllBtn && unselectAllBtn && checkboxesContainer) {
            const checkboxes = checkboxesContainer.querySelectorAll('input[type="checkbox"]');
            if (checkboxes.length > 0) {
                selectAllBtn.addEventListener('click', () => checkboxes.forEach(cb => cb.checked = true));
                unselectAllBtn.addEventListener('click', () => checkboxes.forEach(cb => cb.checked = false));
            }
        }
    }

    // --- Toggle Add Profile Form Visibility on manage_profiles.html ---
    const toggleBtn = document.getElementById('toggleAddProfileFormBtn');
    const addProfileFormContainer = document.getElementById('addProfileFormContainer');
    const cancelAddProfileBtn = document.getElementById('cancelAddProfileBtn');

    if (toggleBtn && addProfileFormContainer) {
        toggleBtn.addEventListener('click', function() {
            const isHidden = addProfileFormContainer.style.display === 'none' || addProfileFormContainer.style.display === '';
            if (isHidden) {
                addProfileFormContainer.style.display = 'block';
                this.innerHTML = '<i class="fas fa-minus-circle"></i> Hide Add Profile Form';
                addProfileFormContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
            } else {
                addProfileFormContainer.style.display = 'none';
                this.innerHTML = '<i class="fas fa-plus-circle"></i> Add New Profile';
            }
        });
    }
    if (cancelAddProfileBtn && addProfileFormContainer && toggleBtn) {
        cancelAddProfileBtn.addEventListener('click', function() {
            addProfileFormContainer.style.display = 'none';
            toggleBtn.innerHTML = '<i class="fas fa-plus-circle"></i> Add New Profile';
        });
    }

    // --- Initialize Author Fields Management ---
    if (document.getElementById('authorsContainerAdd') && document.getElementById('addAuthorBtn')) {
        initializeAuthorManagement('authorsContainerAdd', 'addAuthorBtn', [], 'add');
    }

    const editAuthorsContainer = document.getElementById('authorsContainerEdit');
    if (editAuthorsContainer && document.getElementById('addAuthorBtnEdit')) {
        try {
            const existingAuthorsJson = editAuthorsContainer.dataset.existingAuthors;
            const existingAuthors = (existingAuthorsJson && existingAuthorsJson !== 'null' && existingAuthorsJson.trim() !== '') ? JSON.parse(existingAuthorsJson) : [];
            initializeAuthorManagement('authorsContainerEdit', 'addAuthorBtnEdit', existingAuthors, 'edit');
        } catch (e) {
            console.error("Error parsing existing authors data for edit form:", e, editAuthorsContainer ? editAuthorsContainer.dataset.existingAuthors : 'Container not found');
            initializeAuthorManagement('authorsContainerEdit', 'addAuthorBtnEdit', [], 'edit'); // Fallback
        }
    }
    
    // --- Report Section Checkbox Controls ---
    setupReportSectionControls('Add');
    setupReportSectionControls('Edit');

    // --- Smooth Scroll for Internal Page Links ---
    document.querySelectorAll('.smooth-scroll').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const targetId = this.getAttribute('href');
            if (targetId && targetId.startsWith('#')) {
                const targetElement = document.querySelector(targetId);
                if (targetElement) {
                    targetElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            }
        });
    });

    // --- Automation Runner Page Specific JS ---
    if (document.getElementById('automationRunForm')) {
        console.log("Main JS loaded for Automation Runner Page specific enhancements.");

        window.toggleTickerInput = function(profileId, selectedMethod) {
            const fileSection = document.getElementById(`file_upload_section_${profileId}`);
            const manualSection = document.getElementById(`manual_ticker_section_${profileId}`);
            const fileInput = document.getElementById(`ticker_file_${profileId}`);
            const manualTextarea = document.getElementById(`custom_tickers_${profileId}`);

            if (!fileSection || !manualSection) {
                console.warn(`Ticker input sections not found for profile ${profileId}`);
                return;
            }

            if (selectedMethod === 'file') {
                fileSection.style.display = 'block';
                manualSection.style.display = 'none';
                if (manualTextarea) manualTextarea.value = '';
            } else { // 'manual'
                fileSection.style.display = 'none';
                manualSection.style.display = 'block';
                if (fileInput) fileInput.value = '';

                const fileInfoDiv = document.getElementById(`uploaded_file_info_${profileId}`);
                const tickerTableContainer = document.getElementById(`ticker_table_container_${profileId}`);
                if (fileInfoDiv) fileInfoDiv.style.display = 'none';
                if (tickerTableContainer) tickerTableContainer.style.display = 'none';
            }
        };

        document.querySelectorAll('.profile-run-card').forEach(card => {
            const profileId = card.dataset.profileId;
            if (profileId) {
                // Default to 'file' or check radio buttons
                const selectedMethodInput = card.querySelector(`input[name="ticker_input_method_${profileId}"]:checked`);
                const defaultMethod = selectedMethodInput ? selectedMethodInput.value : 'file';
                toggleTickerInput(profileId, defaultMethod);
            }
        });

        document.querySelectorAll('.ticker-file-input').forEach(input => {
            input.addEventListener('change', function(event) {
                const profileId = this.dataset.profileId;
                const fileInfoDiv = document.getElementById(`uploaded_file_info_${profileId}`);
                const fileNameSpan = fileInfoDiv ? fileInfoDiv.querySelector('.file-name') : null;
                const removeFileBtn = fileInfoDiv ? fileInfoDiv.querySelector('.remove-file-btn') : null;
                const tickerTableContainer = document.getElementById(`ticker_table_container_${profileId}`);
                const tickerTableBody = tickerTableContainer ? tickerTableContainer.querySelector('tbody') : null;

                if (event.target.files && event.target.files[0]) {
                    const file = event.target.files[0];
                    if (fileNameSpan) fileNameSpan.textContent = file.name;
                    if (fileInfoDiv) fileInfoDiv.style.display = 'flex';

                    if (removeFileBtn) {
                        removeFileBtn.style.display = 'inline-block';
                        removeFileBtn.onclick = function() {
                            input.value = ''; // Clear the file input
                            if (fileInfoDiv) fileInfoDiv.style.display = 'none';
                            if (fileNameSpan) fileNameSpan.textContent = '';
                            if (tickerTableContainer) tickerTableContainer.style.display = 'none';
                            if (tickerTableBody) tickerTableBody.innerHTML = '';
                            removeFileBtn.style.display = 'none';
                        };
                    }

                    if (tickerTableContainer && tickerTableBody) {
                        tickerTableBody.innerHTML = `<tr><td colspan="2" style="text-align:center; color:#6c757d; padding:10px;"><i>Preview tickers from '${file.name}'. Status lookup requires backend processing.</i></td></tr>`;
                        tickerTableContainer.style.display = 'block';
                    }
                    const manualTextarea = document.getElementById(`custom_tickers_${profileId}`);
                    if (manualTextarea) manualTextarea.value = ''; // Clear manual input if file is chosen
                } else { // No file selected
                    if (fileInfoDiv) fileInfoDiv.style.display = 'none';
                    if (fileNameSpan) fileNameSpan.textContent = '';
                    if (tickerTableContainer) tickerTableContainer.style.display = 'none';
                    if (tickerTableBody) tickerTableBody.innerHTML = '';
                    if (removeFileBtn) removeFileBtn.style.display = 'none';
                }
            });
        });
    }
    // ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
}); // End of main DOMContentLoaded