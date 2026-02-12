/**
 * Rooting Future - Strategic Plan Viewer v6.0
 * Interactive navigation, search, and export functionality
 */

// ================================================================
// COLLAPSIBLE SECTIONS
// ================================================================

document.addEventListener('DOMContentLoaded', function() {
    // Collapsible section handlers
    const sectionHeaders = document.querySelectorAll('.section-header');

    sectionHeaders.forEach(header => {
        header.addEventListener('click', function() {
            const collapseBtn = this.querySelector('.collapse-btn');
            const targetId = collapseBtn.dataset.target;
            const content = document.getElementById(targetId);

            if (content) {
                content.classList.toggle('collapsed');
                collapseBtn.classList.toggle('collapsed');
            }
        });
    });

    // Initialize navigation
    initSidebarNavigation();

    // Initialize search
    initSearch();
});

// ================================================================
// SIDEBAR NAVIGATION
// ================================================================

function initSidebarNavigation() {
    const navLinks = document.querySelectorAll('.nav-link');
    const sections = document.querySelectorAll('.plan-section');

    // Intersection Observer for scroll-based active state
    const observerOptions = {
        root: null,
        rootMargin: '-20% 0px -60% 0px',
        threshold: 0
    };

    const observer = new IntersectionObserver(entries => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const id = entry.target.id;

                // Update active nav link
                navLinks.forEach(link => {
                    link.classList.remove('active');
                    const href = link.getAttribute('href');
                    if (href === `#${id}`) {
                        link.classList.add('active');
                    }
                });
            }
        });
    }, observerOptions);

    sections.forEach(section => observer.observe(section));

    // Smooth scroll on click
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const targetId = this.getAttribute('href').substring(1);
            const target = document.getElementById(targetId);

            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });

                // Expand section if collapsed
                const content = target.querySelector('.section-content');
                const collapseBtn = target.querySelector('.collapse-btn');
                if (content && content.classList.contains('collapsed')) {
                    content.classList.remove('collapsed');
                    if (collapseBtn) {
                        collapseBtn.classList.remove('collapsed');
                    }
                }
            }
        });
    });
}

// ================================================================
// SEARCH FUNCTIONALITY
// ================================================================

function initSearch() {
    const searchInput = document.getElementById('planSearch');
    if (!searchInput) return;

    let searchTimeout;

    searchInput.addEventListener('input', function() {
        clearTimeout(searchTimeout);
        const query = this.value.toLowerCase().trim();

        if (query.length < 3) {
            clearSearchHighlights();
            return;
        }

        searchTimeout = setTimeout(() => {
            searchInPlan(query);
        }, 300);
    });
}

function searchInPlan(query) {
    clearSearchHighlights();

    const sections = document.querySelectorAll('.plan-section');
    let matchCount = 0;

    sections.forEach(section => {
        const content = section.querySelector('.section-content');
        if (!content) return;

        const text = content.textContent.toLowerCase();

        if (text.includes(query)) {
            // Highlight section
            section.classList.add('search-match');
            matchCount++;

            // Expand section if collapsed
            const collapseBtn = section.querySelector('.collapse-btn');
            if (content.classList.contains('collapsed')) {
                content.classList.remove('collapsed');
                if (collapseBtn) {
                    collapseBtn.classList.remove('collapsed');
                }
            }

            // Scroll to first match
            if (matchCount === 1) {
                setTimeout(() => {
                    section.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }, 100);
            }
        }
    });

    console.log(`[SEARCH] Found ${matchCount} matches for query: "${query}"`);
}

function clearSearchHighlights() {
    document.querySelectorAll('.search-match').forEach(el => {
        el.classList.remove('search-match');
    });
}

// ================================================================
// EXPORT FUNCTIONS
// ================================================================

function exportPDF(planId) {
    console.log('[EXPORT] Starting PDF export for plan:', planId);
    showExportLoadingModal('PDF');

    fetch(`/api/export/${planId}/pdf`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return response.blob();
        })
        .then(blob => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `Piano_Strategico_${planId}.pdf`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            hideExportLoadingModal();
            console.log('[EXPORT] PDF download started successfully');
        })
        .catch(error => {
            console.error('[EXPORT] PDF export failed:', error);
            hideExportLoadingModal();
            showErrorModal('Errore durante l\'esportazione PDF', error.message);
        });
}

function exportDOCX(planId) {
    console.log('[EXPORT] Starting DOCX export for plan:', planId);
    window.location.href = `/api/export/${planId}/docx`;
}

function exportOnePager(planId) {
    console.log('[EXPORT] Starting OnePager export for plan:', planId);
    window.location.href = `/api/export/${planId}/onepager`;
}

// ================================================================
// MODAL MANAGEMENT
// ================================================================

function showExportLoadingModal(format) {
    const modal = document.getElementById('exportModal');
    if (!modal) return;

    const title = document.getElementById('exportModalTitle');
    const desc = document.getElementById('exportModalDesc');

    if (title) {
        title.textContent = `Generazione ${format} in corso...`;
    }

    if (desc) {
        if (format === 'PDF') {
            desc.textContent = 'Questo potrebbe richiedere fino a 30 secondi';
        } else {
            desc.textContent = 'Attendere prego...';
        }
    }

    modal.style.display = 'flex';
    console.log(`[MODAL] Showing export modal for format: ${format}`);
}

function hideExportLoadingModal() {
    const modal = document.getElementById('exportModal');
    if (modal) {
        modal.style.display = 'none';
        console.log('[MODAL] Export modal hidden');
    }
}

function showErrorModal(title, message) {
    alert(`${title}\n\n${message}\n\nRiprova o contatta il supporto.`);
}

// ================================================================
// KEYBOARD SHORTCUTS
// ================================================================

document.addEventListener('keydown', function(e) {
    // Ctrl/Cmd + K: Focus search
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        const searchInput = document.getElementById('planSearch');
        if (searchInput) {
            searchInput.focus();
        }
    }

    // Ctrl/Cmd + P: Print
    if ((e.ctrlKey || e.metaKey) && e.key === 'p') {
        // Let browser handle print
        console.log('[PRINT] Print dialog triggered');
    }

    // Escape: Clear search
    if (e.key === 'Escape') {
        const searchInput = document.getElementById('planSearch');
        if (searchInput && searchInput.value) {
            searchInput.value = '';
            clearSearchHighlights();
        }
    }
});

// ================================================================
// UTILITY FUNCTIONS
// ================================================================

// Expand all sections
function expandAll() {
    document.querySelectorAll('.section-content.collapsed').forEach(content => {
        content.classList.remove('collapsed');
    });
    document.querySelectorAll('.collapse-btn.collapsed').forEach(btn => {
        btn.classList.remove('collapsed');
    });
    console.log('[UI] All sections expanded');
}

// Collapse all sections
function collapseAll() {
    document.querySelectorAll('.section-content').forEach(content => {
        content.classList.add('collapsed');
    });
    document.querySelectorAll('.collapse-btn').forEach(btn => {
        btn.classList.add('collapsed');
    });
    console.log('[UI] All sections collapsed');
}

// ================================================================
// SHARE FUNCTIONALITY (FEAT-008)
// ================================================================

function openShareModal() {
    const modal = document.getElementById('shareModal');
    if (!modal) return;

    modal.style.display = 'flex';
    loadActiveShares();
    console.log('[SHARE] Modal opened');
}

function closeShareModal() {
    const modal = document.getElementById('shareModal');
    if (modal) {
        modal.style.display = 'none';
        // Reset form
        document.getElementById('shareForm').reset();
        document.getElementById('shareResult').style.display = 'none';
        console.log('[SHARE] Modal closed');
    }
}

// Handle share form submission
document.addEventListener('DOMContentLoaded', function() {
    const shareForm = document.getElementById('shareForm');
    if (shareForm) {
        shareForm.addEventListener('submit', function(e) {
            e.preventDefault();

            const planId = document.body.dataset.planId;
            const formData = new FormData(shareForm);

            const data = {
                expires_days: parseInt(formData.get('expires_days')),
                password: formData.get('password') || null,
                allow_download: formData.get('allow_download') === 'on'
            };

            console.log('[SHARE] Creating share link...', data);

            fetch(`/share/${planId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            })
            .then(response => response.json())
            .then(result => {
                if (result.success) {
                    console.log('[SHARE] Share link created:', result.share_url);

                    // Show result
                    document.getElementById('shareUrl').value = result.share_url;
                    document.getElementById('shareResult').style.display = 'block';

                    // Reload active shares
                    loadActiveShares();

                    // Scroll to result
                    document.getElementById('shareResult').scrollIntoView({ behavior: 'smooth' });
                } else {
                    alert('Errore durante la creazione del link: ' + (result.error || 'Errore sconosciuto'));
                }
            })
            .catch(error => {
                console.error('[SHARE] Error creating share:', error);
                alert('Errore durante la creazione del link di condivisione.');
            });
        });
    }
});

function copyShareUrl() {
    const input = document.getElementById('shareUrl');
    if (!input) return;

    input.select();
    input.setSelectionRange(0, 99999); // For mobile

    navigator.clipboard.writeText(input.value)
        .then(() => {
            console.log('[SHARE] URL copied to clipboard');
            const btn = event.target;
            const originalText = btn.textContent;
            btn.textContent = '✅ Copiato!';
            setTimeout(() => {
                btn.textContent = originalText;
            }, 2000);
        })
        .catch(err => {
            console.error('[SHARE] Failed to copy:', err);
            // Fallback
            document.execCommand('copy');
        });
}

function loadActiveShares() {
    const planId = document.body.dataset.planId;
    const sharesList = document.getElementById('sharesList');

    if (!sharesList) return;

    sharesList.innerHTML = '<p style="color: #6c757d; font-size: 14px;">Caricamento...</p>';

    fetch(`/api/shares/${planId}`)
        .then(response => response.json())
        .then(data => {
            const shares = data.shares || [];

            if (shares.length === 0) {
                sharesList.innerHTML = '<p style="color: #6c757d; font-size: 14px;">Nessun link attivo. Crea il primo!</p>';
                return;
            }

            let html = '';
            shares.forEach(share => {
                const expiresAt = new Date(share.expires_at);
                const createdAt = new Date(share.created_at);

                html += `
                    <div class="share-item">
                        <div class="share-item-info">
                            <strong>${share.share_url.substring(0, 60)}...</strong>
                            <small>
                                Creato: ${createdAt.toLocaleDateString('it-IT')} |
                                Scade: ${expiresAt.toLocaleDateString('it-IT')} |
                                Visualizzazioni: ${share.view_count}
                                ${share.password_hash ? ' | 🔐 Protetto' : ''}
                                ${share.allow_download ? ' | 📥 Download' : ''}
                            </small>
                        </div>
                        <button class="btn-revoke" onclick="revokeShare('${share.share_token}')">
                            🗑️ Revoca
                        </button>
                    </div>
                `;
            });

            sharesList.innerHTML = html;
            console.log('[SHARE] Loaded', shares.length, 'active shares');
        })
        .catch(error => {
            console.error('[SHARE] Error loading shares:', error);
            sharesList.innerHTML = '<p style="color: #dc2626; font-size: 14px;">Errore nel caricamento dei link.</p>';
        });
}

function revokeShare(shareToken) {
    if (!confirm('Sei sicuro di voler revocare questo link? Non sarà più accessibile.')) {
        return;
    }

    console.log('[SHARE] Revoking share:', shareToken);

    fetch(`/api/shares/${shareToken}/revoke`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            console.log('[SHARE] Share revoked successfully');
            loadActiveShares();
        } else {
            alert('Errore durante la revoca: ' + (result.error || 'Errore sconosciuto'));
        }
    })
    .catch(error => {
        console.error('[SHARE] Error revoking share:', error);
        alert('Errore durante la revoca del link.');
    });
}

// Close modal on background click
document.addEventListener('click', function(e) {
    const shareModal = document.getElementById('shareModal');
    if (e.target === shareModal) {
        closeShareModal();
    }
});

// Log page load
console.log('[PLAN VIEWER] Page loaded successfully');
console.log('[PLAN VIEWER] Plan ID:', document.body.dataset.planId);
