function initializeReportDisplay(reportUrlData) {
    const iframe = document.getElementById('report-iframe');
    const loadingMessage = document.querySelector('.loading-message');
    const reportArea = document.getElementById('report-content-area');
    const reportUrl = reportUrlData; // reportUrlData is passed from the template

    if (!iframe || !reportArea) {
        return;
    }
    if (loadingMessage) {
        // console.log("Loading message element found.");
    }

    let resizeTimer; 

    function resizePlotlyPlots() {
        try {
            if (!iframe.contentWindow || !iframe.contentWindow.document || !iframe.contentWindow.Plotly) {
                return;
            }
            const plotlyInstance = iframe.contentWindow.Plotly;
            if (plotlyInstance && typeof plotlyInstance.Plots !== 'undefined' && typeof plotlyInstance.Plots.resize === 'function') {
                const plotDivs = iframe.contentWindow.document.querySelectorAll('.plotly-graph-div');
                if (plotDivs.length > 0) {
                    plotDivs.forEach(div => {
                        try {
                            if (div.offsetParent !== null) { 
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
                iframe.style.height = '100vh'; 
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
             iframe.style.height = '120vh'; 
         }
    }

    if (reportUrl && reportUrl !== 'None' && reportUrl.trim() !== '' && reportUrl.trim() !== '#') {
        iframe.src = reportUrl;

        iframe.onload = function() {
            if (loadingMessage) { 
                loadingMessage.style.display = 'none';
            }
            iframe.style.visibility = 'visible';

            let attempts = 0;
            const maxAttempts = 5; 
            function attemptAdjustments() {
                if (!iframe.contentWindow || !iframe.contentWindow.document || !iframe.contentWindow.document.body || iframe.contentWindow.document.readyState !== 'complete') {
                    if (attempts < maxAttempts) {
                        attempts++;
                        setTimeout(attemptAdjustments, 250 + (attempts * 50)); 
                        return;
                    } else {
                        console.warn("Max attempts for iframe readiness reached. Trying final adjustment.");
                    }
                }

                resizePlotlyPlots();
                adjustIframeHeight();
                
                attempts++; 
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
                       if(iframe.contentWindow) { 
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
            setTimeout(attemptAdjustments, 250); 
        };

        iframe.onerror = function() {
            if (reportArea) { 
                reportArea.innerHTML = '<p class="error-message">Error: Failed to load report content. The file might be missing or inaccessible.</p>';
            }
            if (loadingMessage) { 
                loadingMessage.style.display = 'none';
            }
        };
    } else {
        if (reportArea) { 
            reportArea.innerHTML = '<p class="error-message">Error: Invalid or missing report URL.</p>';
        }
        if (loadingMessage) { 
            loadingMessage.style.display = 'none';
        }
    }
}


document.addEventListener('DOMContentLoaded', function() {
    console.log("Main JavaScript Initializing (with report display and automation runner logic)..."); 

    const reportIframeElement = document.getElementById('report-iframe');
    if (reportIframeElement && reportIframeElement.hasAttribute('data-report-url')) {
        const reportUrlForDisplay = reportIframeElement.getAttribute('data-report-url');
        if (typeof initializeReportDisplay === 'function') {
            initializeReportDisplay(reportUrlForDisplay);
        } else {
            console.error("initializeReportDisplay function is not defined. Check main.js structure.");
        }
    }

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
        if (!writerEntry) return;
        const container = writerEntry.parentElement;
        writerEntry.remove();
        const remainingEntries = container.querySelectorAll('.writer-entry');
        remainingEntries.forEach((entry, idx) => {
            const heading = entry.querySelector('h4');
            if (heading) {
                const btn = heading.querySelector('.remove-writer-btn');
                heading.textContent = `Writer ${idx + 1} `;
                if (btn) heading.appendChild(btn);
            }
        });
    }

    function initializeAuthorManagement(containerId, addButtonId, existingAuthorsData = [], formType = 'add') {
        const addAuthorBtn = document.getElementById(addButtonId);
        const container = document.getElementById(containerId);
        if (!addAuthorBtn || !container) return;
        container.querySelectorAll('.writer-entry').forEach(entry => entry.remove());
        if (existingAuthorsData && existingAuthorsData.length > 0) {
            existingAuthorsData.forEach(author => addWriterFields(containerId, author, formType));
        } else {
            if (formType === 'add') addWriterFields(containerId, null, formType);
        }
        addAuthorBtn.onclick = function() { addWriterFields(containerId, null, formType); };
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

    const toggleBtn = document.getElementById('toggleAddProfileFormBtn');
    const addProfileFormContainer = document.getElementById('addProfileFormContainer');
    const cancelAddProfileBtn = document.getElementById('cancelAddProfileBtn');
    if (toggleBtn && addProfileFormContainer) {
        toggleBtn.addEventListener('click', function() {
            const isHidden = addProfileFormContainer.style.display === 'none' || addProfileFormContainer.style.display === '';
            addProfileFormContainer.style.display = isHidden ? 'block' : 'none';
            this.innerHTML = isHidden ? '<i class="fas fa-minus-circle"></i> Hide Add Profile Form' : '<i class="fas fa-plus-circle"></i> Add New Profile';
            if (isHidden) addProfileFormContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
    }
    if (cancelAddProfileBtn && addProfileFormContainer && toggleBtn) {
        cancelAddProfileBtn.addEventListener('click', function() {
            addProfileFormContainer.style.display = 'none';
            toggleBtn.innerHTML = '<i class="fas fa-plus-circle"></i> Add New Profile';
        });
    }

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
            initializeAuthorManagement('authorsContainerEdit', 'addAuthorBtnEdit', [], 'edit'); 
        }
    }
    
    setupReportSectionControls('Add');
    setupReportSectionControls('Edit');

    document.querySelectorAll('.smooth-scroll').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const targetId = this.getAttribute('href');
            if (targetId && targetId.startsWith('#')) {
                const targetElement = document.querySelector(targetId);
                if (targetElement) targetElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });

    // --- Automation Runner Page Specific JS ---
    if (document.getElementById('automationRunForm')) {
        console.log("Main JS loaded for Automation Runner Page specific enhancements.");

        // Helper function to get the correct prefix for element IDs based on ticker source
        function getElementPrefixForProfile(profileId) {
            const selectedMethodInput = document.querySelector(`input[name="ticker_source_${profileId}"]:checked`);
            return (selectedMethodInput && selectedMethodInput.value === 'manual') ? 'manual_' : '';
        }

        // Helper function to reset progress and table for a profile
        function resetProfileRunUI(profileId) {
            ['', 'manual_'].forEach(prefix => {
                const progressDisplay = document.getElementById(`${prefix}progress_display_${profileId}`);
                if (progressDisplay) progressDisplay.style.display = 'none';
                const processedCount = document.getElementById(`${prefix}processed_count_${profileId}`);
                if (processedCount) processedCount.textContent = '0';
                const totalCount = document.getElementById(`${prefix}total_count_${profileId}`);
                if (totalCount) totalCount.textContent = '0';
                const tableContainer = document.getElementById(`${prefix}ticker_table_container_${profileId}`);
                if (tableContainer) tableContainer.style.display = 'none';
                const tableBody = document.querySelector(`#${prefix}status_table_for_${profileId} tbody`);
                if (tableBody) tableBody.innerHTML = '';
            });
        }
        
        // Helper function to update ticker status table (NEW from previous discussion)
        function updateTickerStatusTable(profileId, tickerData) {
            const methodPrefix = getElementPrefixForProfile(profileId);
            const tableBodyId = `${methodPrefix}status_table_for_${profileId}`;
            const tableBody = document.querySelector(`#${tableBodyId} tbody`);
            
            if (tableBody) {
                let row = tableBody.querySelector(`tr[data-ticker="${tickerData.ticker}"]`);
                if (!row) {
                    row = tableBody.insertRow(0); // Insert new tickers at the top
                    row.setAttribute('data-ticker', tickerData.ticker);
                    row.innerHTML = `
                        <td>${tickerData.ticker}</td>
                        <td class="generation-time">Pending</td>
                        <td class="publish-time">Pending</td>
                        <td class="writer-username">N/A</td>
                        <td class="status">Processing</td>
                    `;
                }
                
                row.querySelector('.generation-time').textContent = tickerData.generation_time ? new Date(tickerData.generation_time).toLocaleString() : 'Pending';
                row.querySelector('.publish-time').textContent = tickerData.publish_time ? new Date(tickerData.publish_time).toLocaleString() : 'Pending';
                row.querySelector('.writer-username').textContent = tickerData.writer_username || 'N/A';
                const statusCell = row.querySelector('.status');
                statusCell.textContent = tickerData.status || 'Processing';
                statusCell.className = `status status-${(tickerData.status || 'processing').toLowerCase().replace(/[^a-z0-9-]+/g, '-')}`;

                // Make table visible if it was hidden
                const tableContainer = document.getElementById(`${methodPrefix}ticker_table_container_${profileId}`);
                if(tableContainer) tableContainer.style.display = 'block';

            } else {
                console.warn(`Table body not found for profile ${profileId} with prefix '${methodPrefix}' (ID: ${tableBodyId})`);
            }
        }


        window.toggleTickerInput = function(profileId, selectedMethod) {
            const fileSection = document.getElementById(`file_upload_section_${profileId}`);
            const manualSection = document.getElementById(`manual_ticker_section_${profileId}`);
            const fileInput = document.getElementById(`ticker_file_${profileId}`);
            const manualTextarea = document.getElementById(`custom_tickers_${profileId}`);

            if (!fileSection || !manualSection) {
                console.warn(`Ticker input sections not found for profile ${profileId}`);
                return;
            }

            // Reset UI for both sections before showing the selected one
            resetProfileRunUI(profileId); 
            // If file was selected, clear its info too
            const fileInfoDiv = document.getElementById(`uploaded_file_info_${profileId}`);
            if (fileInfoDiv) fileInfoDiv.style.display = 'none';


            if (selectedMethod === 'file') {
                fileSection.style.display = 'block';
                manualSection.style.display = 'none';
                if (manualTextarea) manualTextarea.value = '';
            } else { // 'manual'
                fileSection.style.display = 'none';
                manualSection.style.display = 'block';
                if (fileInput) fileInput.value = '';
                // if (fileInfoDiv) fileInfoDiv.style.display = 'none'; // Already handled by resetProfileRunUI indirectly
            }
        };

        document.querySelectorAll('.profile-run-card').forEach(card => {
            const profileId = card.dataset.profileId;
            if (profileId) {
                const selectedMethodInput = card.querySelector(`input[name="ticker_source_${profileId}"]:checked`);
                const defaultMethod = selectedMethodInput ? selectedMethodInput.value : 'file';
                toggleTickerInput(profileId, defaultMethod); // Initialize display based on checked radio or default
            }
        });

        document.querySelectorAll('.ticker-file-input').forEach(input => {
            input.addEventListener('change', function(event) {
                const profileId = this.dataset.profileId;
                const fileInfoDiv = document.getElementById(`uploaded_file_info_${profileId}`);
                const fileNameSpan = fileInfoDiv ? fileInfoDiv.querySelector('.file-name') : null;
                const removeFileBtn = fileInfoDiv ? fileInfoDiv.querySelector('.remove-file-btn') : null;
                
                // For file uploads, use the non-prefixed table and progress
                const tickerTableContainer = document.getElementById(`ticker_table_container_${profileId}`);
                const tickerTableBody = tickerTableContainer ? tickerTableContainer.querySelector('tbody') : null;
                const progressDisplay = document.getElementById(`progress_display_${profileId}`);


                if (event.target.files && event.target.files[0]) {
                    const file = event.target.files[0];
                    if (fileNameSpan) fileNameSpan.textContent = file.name;
                    if (fileInfoDiv) fileInfoDiv.style.display = 'flex';

                    if (removeFileBtn) {
                        removeFileBtn.style.display = 'inline-block';
                        removeFileBtn.onclick = function() {
                            input.value = ''; 
                            if (fileInfoDiv) fileInfoDiv.style.display = 'none';
                            if (fileNameSpan) fileNameSpan.textContent = '';
                            if (tickerTableContainer) tickerTableContainer.style.display = 'none';
                            if (tickerTableBody) tickerTableBody.innerHTML = '';
                            if (progressDisplay) progressDisplay.style.display = 'none';
                            // Also reset counts if file is removed
                            const processedCountEl = document.getElementById(`processed_count_${profileId}`);
                            const totalCountEl = document.getElementById(`total_count_${profileId}`);
                            if(processedCountEl) processedCountEl.textContent = '0';
                            if(totalCountEl) totalCountEl.textContent = '0';
                            removeFileBtn.style.display = 'none';
                        };
                    }
                    // Initial message in the table body for file uploads
                    if (tickerTableBody) {
                        tickerTableBody.innerHTML = `<tr><td colspan="5" style="text-align:center; color:#6c757d; padding:0.75rem;"><i>Tickers from '${file.name}' will appear here once processing starts.</i></td></tr>`;
                    }
                    // Table container visibility will be handled by socket updates
                    if (tickerTableContainer) tickerTableContainer.style.display = 'none'; 
                    if (progressDisplay) progressDisplay.style.display = 'none'; // Hide progress until total count known

                    const manualTextarea = document.getElementById(`custom_tickers_${profileId}`);
                    if (manualTextarea) manualTextarea.value = ''; 
                } else { 
                    if (fileInfoDiv) fileInfoDiv.style.display = 'none';
                    if (fileNameSpan) fileNameSpan.textContent = '';
                    if (tickerTableContainer) tickerTableContainer.style.display = 'none';
                    if (tickerTableBody) tickerTableBody.innerHTML = '';
                    if (progressDisplay) progressDisplay.style.display = 'none';
                    if (removeFileBtn) removeFileBtn.style.display = 'none';
                }
            });
        });

        // SocketIO Listeners Specific to Automation Runner Page
        if (typeof io !== 'undefined') {
            const socket = io(); // Assuming socket is connected as per firebase-init.js or _base.html

            socket.on('automation_update', function(data) {
                if (data.profile_id && data.profile_id !== "Overall") {
                    const methodPrefix = getElementPrefixForProfile(data.profile_id);
                    
                    // Handle total ticker count updates
                    if (data.phase === "Ticker Loading" && (data.stage === "File" || data.stage === "Custom")) {
                        let totalTickers = 0;
                        if (data.stage === "File" && data.message && data.message.startsWith("Found ")) {
                            const match = data.message.match(/Found (\d+) tickers/);
                            if (match) totalTickers = parseInt(match[1]);
                        } else if (data.stage === "Custom" && data.message && data.message.startsWith("Processing ")) {
                            const match = data.message.match(/Processing (\d+) custom tickers/);
                            if (match) totalTickers = parseInt(match[1]);
                        }

                        const totalCountEl = document.getElementById(`${methodPrefix}total_count_${data.profile_id}`);
                        const processedCountEl = document.getElementById(`${methodPrefix}processed_count_${data.profile_id}`);
                        const progressDisplayEl = document.getElementById(`${methodPrefix}progress_display_${data.profile_id}`);
                        const tableContainerEl = document.getElementById(`${methodPrefix}ticker_table_container_${data.profile_id}`);
                        const tableBodyEl = document.querySelector(`#${methodPrefix}status_table_for_${data.profile_id} tbody`);


                        if (totalCountEl) totalCountEl.textContent = totalTickers;
                        if (processedCountEl) processedCountEl.textContent = '0';
                        if (progressDisplayEl) progressDisplayEl.style.display = (totalTickers > 0) ? 'block' : 'none';
                        if (tableBodyEl) tableBodyEl.innerHTML = ''; // Clear previous table entries
                        if (tableContainerEl) tableContainerEl.style.display = (totalTickers > 0) ? 'block' : 'none';
                    }
                }
            });

            socket.on('ticker_processed_update', function(data) {
                if (data.profile_id && data.ticker) {
                    updateTickerStatusTable(data.profile_id, data); // Use the helper function
                    
                    const methodPrefix = getElementPrefixForProfile(data.profile_id);
                    const processedCountEl = document.getElementById(`${methodPrefix}processed_count_${data.profile_id}`);
                    const totalCountEl = document.getElementById(`${methodPrefix}total_count_${data.profile_id}`);

                    if (processedCountEl && totalCountEl) {
                        // Increment processed count only for final states
                        let isFinalState = ['Published', 'Skipped'].includes(data.status) || 
                                           (typeof data.status === 'string' && (data.status.startsWith("Failed") || data.status.startsWith("Halted")));
                        
                        const tableBody = document.querySelector(`#${methodPrefix}status_table_for_${data.profile_id} tbody`);
                        const tickerRow = tableBody ? tableBody.querySelector(`tr[data-ticker="${data.ticker}"]`) : null;

                        if (isFinalState && tickerRow && !tickerRow.dataset.countedAsProcessed) {
                            let currentProcessed = parseInt(processedCountEl.textContent) || 0;
                            processedCountEl.textContent = currentProcessed + 1;
                            tickerRow.dataset.countedAsProcessed = "true"; // Mark as counted
                        }
                        
                        let total = parseInt(totalCountEl.textContent) || 0;
                        let finalProcessedCount = parseInt(processedCountEl.textContent) || 0;

                        if (total > 0) {
                            const progressPercent = Math.min(100, (finalProcessedCount / total) * 100);
                            // progressBarEl.style.width = `${progressPercent}%`;
                            // progressBarEl.textContent = `${Math.round(progressPercent)}%`;
                            // progressBarEl.setAttribute('aria-valuenow', progressPercent);
                        }
                    }
                }
            });
             // Reset UI elements for selected profiles when form is submitted
            const form = document.getElementById('automationRunForm');
            if(form){
                form.addEventListener('submit', function() {
                    document.querySelectorAll('.profile-run-card input[type="checkbox"]:checked').forEach(checkbox => {
                        const profileId = checkbox.value;
                        resetProfileRunUI(profileId); // Reset UI for the selected profile
                    });
                });
            }
        } else {
            console.warn("Socket.IO not loaded, real-time updates on Automation Runner page will not work.");
        }
    } // End of Automation Runner Page Specific JS
}); // End of main DOMContentLoaded