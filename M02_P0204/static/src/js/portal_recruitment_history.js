/* eslint-disable no-undef */
(function () {
    var SEARCH_DEBOUNCE_MS = 450;
    var RECRUITMENT_CARD_SELECTOR = '.portal-recruitment-tabs-card';
    var pendingFetchController = null;
    var searchTimers = {
        jobs: null,
        history: null,
    };

    function normalizeUrl(url) {
        var parsedUrl = new URL(url, window.location.origin);
        return parsedUrl.pathname + (parsedUrl.search ? parsedUrl.search : '');
    }

    function getCurrentUrl() {
        return window.location.pathname + (window.location.search ? window.location.search : '');
    }

    function findSummaryRow(table, requestId) {
        return table.querySelector('.portal-recruitment-history-row[data-request-id="' + requestId + '"]');
    }

    function findDetailRow(table, requestId) {
        return table.querySelector('.portal-recruitment-history-detail-row[data-detail-request-id="' + requestId + '"]');
    }

    function closeAllDetails(table) {
        table.querySelectorAll('.portal-recruitment-history-row').forEach(function (row) {
            row.classList.remove('is-active');
            row.setAttribute('aria-expanded', 'false');
        });

        table.querySelectorAll('.portal-recruitment-history-detail-row').forEach(function (detailRow) {
            detailRow.classList.add('d-none');
            detailRow.classList.remove('is-open');
            detailRow.setAttribute('aria-hidden', 'true');
        });
    }

    function setLoadingState(isLoading) {
        var card = document.querySelector(RECRUITMENT_CARD_SELECTOR);
        if (!card) {
            return;
        }
        card.classList.toggle('is-loading', !!isLoading);
    }

    function clearSearchTimer(scope) {
        if (!scope || !searchTimers[scope]) {
            return;
        }
        window.clearTimeout(searchTimers[scope]);
        searchTimers[scope] = null;
    }

    function clearAllSearchTimers() {
        clearSearchTimer('jobs');
        clearSearchTimer('history');
    }

    function updateUrlState(activeTab, expandedRequestId, mode) {
        var url = new URL(window.location.href);
        if (activeTab) {
            url.searchParams.set('active_tab', activeTab);
        }
        if (expandedRequestId) {
            url.searchParams.set('expanded_request_id', String(expandedRequestId));
        } else {
            url.searchParams.delete('expanded_request_id');
        }
        var nextUrl = url.pathname + (url.search ? url.search : '');
        if (mode === 'push') {
            window.history.pushState({}, '', nextUrl);
        } else {
            window.history.replaceState({}, '', nextUrl);
        }
        return nextUrl;
    }

    function syncTabHeaderFromDocument(nextDocument) {
        ['portal_jobs_tab', 'portal_request_history_tab'].forEach(function (tabId) {
            var currentTab = document.getElementById(tabId);
            var nextTab = nextDocument.getElementById(tabId);
            if (!currentTab || !nextTab) {
                return;
            }
            currentTab.className = nextTab.className;
            currentTab.setAttribute('aria-selected', nextTab.getAttribute('aria-selected') || 'false');
        });
    }

    function syncPaneFromDocument(nextDocument, paneId) {
        var currentPane = document.getElementById(paneId);
        var nextPane = nextDocument.getElementById(paneId);
        if (!currentPane || !nextPane) {
            return false;
        }
        currentPane.className = nextPane.className;
        currentPane.innerHTML = nextPane.innerHTML;
        return true;
    }

    function restoreExpandedDetailState() {
        var table = document.querySelector('.portal-recruitment-history-table');
        if (!table) {
            return;
        }
        var expandedRequestId = (table.dataset.expandedRequestId || '').trim();
        closeAllDetails(table);
        if (!expandedRequestId) {
            return;
        }
        openDetail(table, expandedRequestId);
    }

    function abortPendingFetch() {
        if (!pendingFetchController) {
            return;
        }
        pendingFetchController.abort();
        pendingFetchController = null;
    }

    function fetchAndRender(nextUrl, options) {
        var settings = options || {};
        var historyMode = settings.historyMode || 'push';
        var normalizedUrl = normalizeUrl(nextUrl);

        clearAllSearchTimers();
        abortPendingFetch();

        var controller = new AbortController();
        pendingFetchController = controller;
        setLoadingState(true);

        return window.fetch(normalizedUrl, {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
            },
            signal: controller.signal,
        }).then(function (response) {
            if (!response.ok) {
                throw new Error('Failed to load recruitment content');
            }
            return response.text();
        }).then(function (html) {
            if (controller.signal.aborted) {
                return false;
            }

            var parser = new DOMParser();
            var nextDocument = parser.parseFromString(html, 'text/html');
            var hasJobsPane = syncPaneFromDocument(nextDocument, 'portal_jobs_pane');
            var hasHistoryPane = syncPaneFromDocument(nextDocument, 'portal_request_history_pane');

            if (!hasJobsPane || !hasHistoryPane) {
                window.location.assign(normalizedUrl);
                return false;
            }

            syncTabHeaderFromDocument(nextDocument);
            restoreExpandedDetailState();

            if (historyMode === 'push') {
                window.history.pushState({}, '', normalizedUrl);
            } else if (historyMode === 'replace') {
                window.history.replaceState({}, '', normalizedUrl);
            }
            return true;
        }).catch(function (error) {
            if (error && error.name === 'AbortError') {
                return false;
            }
            window.location.assign(normalizedUrl);
            return false;
        }).finally(function () {
            if (pendingFetchController === controller) {
                pendingFetchController = null;
            }
            setLoadingState(false);
        });
    }

    function openDetail(table, requestId) {
        var summaryRow = findSummaryRow(table, requestId);
        var detailRow = findDetailRow(table, requestId);
        if (!summaryRow || !detailRow) {
            return false;
        }

        closeAllDetails(table);

        summaryRow.classList.add('is-active');
        summaryRow.setAttribute('aria-expanded', 'true');
        detailRow.classList.remove('d-none');
        detailRow.classList.add('is-open');
        detailRow.setAttribute('aria-hidden', 'false');
        return true;
    }

    function toggleDetail(table, requestId) {
        var summaryRow = findSummaryRow(table, requestId);
        if (!summaryRow) {
            return;
        }

        var isActive = summaryRow.classList.contains('is-active');
        if (isActive) {
            closeAllDetails(table);
            table.dataset.expandedRequestId = '';
            updateUrlState('history', '', 'replace');
            return;
        }

        if (openDetail(table, requestId)) {
            table.dataset.expandedRequestId = String(requestId);
            updateUrlState('history', requestId, 'replace');
        }
    }

    function getFormNavigationUrl(form, scope, options) {
        var settings = options || {};
        var resetPage = settings.resetPage !== false;
        var clearExpanded = !!settings.clearExpanded;
        var actionUrl = new URL(form.getAttribute('action') || window.location.pathname, window.location.origin);
        var params = new URLSearchParams();

        new FormData(form).forEach(function (value, key) {
            if (value === null || value === undefined || value === '') {
                return;
            }
            params.set(key, value);
        });

        params.set('active_tab', scope);
        if (resetPage) {
            if (scope === 'jobs') {
                params.set('job_page', '1');
            }
            if (scope === 'history') {
                params.set('history_page', '1');
            }
        }
        if (clearExpanded) {
            params.delete('expanded_request_id');
        }

        actionUrl.search = params.toString();
        return actionUrl.pathname + (actionUrl.search ? actionUrl.search : '');
    }

    function navigateByForm(form, scope, options) {
        fetchAndRender(getFormNavigationUrl(form, scope, options), {
            historyMode: (options && options.historyMode) || 'push',
        });
    }

    function getScopeFromForm(form) {
        var scope = (form.dataset.filterScope || '').trim();
        return scope === 'jobs' || scope === 'history' ? scope : '';
    }

    function handleSearchInput(control) {
        var form = control.closest('.portal-recruitment-smart-filter');
        if (!form) {
            return;
        }
        var scope = getScopeFromForm(form);
        if (!scope) {
            return;
        }

        clearSearchTimer(scope);
        searchTimers[scope] = window.setTimeout(function () {
            if (!document.body.contains(form)) {
                return;
            }
            navigateByForm(form, scope, {
                resetPage: true,
                clearExpanded: true,
                historyMode: 'push',
            });
        }, SEARCH_DEBOUNCE_MS);
    }

    function handleSearchEnter(control, event) {
        if (event.key !== 'Enter') {
            return;
        }

        var form = control.closest('.portal-recruitment-smart-filter');
        if (!form) {
            return;
        }
        var scope = getScopeFromForm(form);
        if (!scope) {
            return;
        }

        event.preventDefault();
        clearSearchTimer(scope);
        navigateByForm(form, scope, {
            resetPage: true,
            clearExpanded: true,
            historyMode: 'push',
        });
    }

    function handleSelectChange(control) {
        var form = control.closest('.portal-recruitment-smart-filter');
        if (!form) {
            return;
        }
        var scope = getScopeFromForm(form);
        if (!scope) {
            return;
        }

        clearSearchTimer(scope);
        navigateByForm(form, scope, {
            resetPage: true,
            clearExpanded: true,
            historyMode: 'push',
        });
    }

    function handleClearFilters(button, event) {
        var form = button.closest('.portal-recruitment-smart-filter');
        if (!form) {
            return;
        }
        var scope = getScopeFromForm(form);
        if (!scope || button.dataset.clearFilters !== scope) {
            return;
        }

        event.preventDefault();
        clearSearchTimer(scope);

        form.querySelectorAll('[data-filter-control="1"]').forEach(function (control) {
            var defaultValue = control.dataset.defaultValue;
            control.value = defaultValue !== undefined ? defaultValue : '';
        });

        navigateByForm(form, scope, {
            resetPage: true,
            clearExpanded: true,
            historyMode: 'push',
        });
    }

    function handleFilterFormSubmit(form, event) {
        var scope = getScopeFromForm(form);
        if (!scope) {
            return;
        }

        event.preventDefault();
        clearSearchTimer(scope);
        navigateByForm(form, scope, {
            resetPage: false,
            clearExpanded: scope === 'history',
            historyMode: 'push',
        });
    }

    function handlePagerClick(link, event) {
        var href = link.getAttribute('href') || '';
        if (!href || href === '#' || link.closest('.page-item.disabled')) {
            return;
        }

        event.preventDefault();
        fetchAndRender(href, { historyMode: 'push' });
    }

    function initTabState() {
        var jobsTab = document.getElementById('portal_jobs_tab');
        var historyTab = document.getElementById('portal_request_history_tab');

        if (jobsTab) {
            jobsTab.addEventListener('click', function () {
                updateUrlState('jobs', '', 'replace');
            });
        }

        if (historyTab) {
            historyTab.addEventListener('click', function () {
                var table = document.querySelector('.portal-recruitment-history-table');
                var expandedRequestId = table ? (table.dataset.expandedRequestId || '').trim() : '';
                updateUrlState('history', expandedRequestId, 'replace');
            });
        }
    }

    function initEventDelegation() {
        document.addEventListener('input', function (event) {
            var searchControl = event.target.closest('[data-filter-control="1"][data-filter-type="search"]');
            if (!searchControl) {
                return;
            }
            handleSearchInput(searchControl);
        });

        document.addEventListener('keydown', function (event) {
            var searchControl = event.target.closest('[data-filter-control="1"][data-filter-type="search"]');
            if (!searchControl) {
                return;
            }
            handleSearchEnter(searchControl, event);
        });

        document.addEventListener('change', function (event) {
            var selectControl = event.target.closest('[data-filter-control="1"][data-filter-type="select"]');
            if (!selectControl) {
                return;
            }
            handleSelectChange(selectControl);
        });

        document.addEventListener('click', function (event) {
            var clearButton = event.target.closest('[data-clear-filters]');
            if (clearButton) {
                handleClearFilters(clearButton, event);
                return;
            }

            var pagerLink = event.target.closest('.portal-recruitment-tab-pager .page-link');
            if (pagerLink && pagerLink.closest(RECRUITMENT_CARD_SELECTOR)) {
                handlePagerClick(pagerLink, event);
                return;
            }

            var summaryRow = event.target.closest('.portal-recruitment-history-row');
            if (!summaryRow) {
                return;
            }
            var table = summaryRow.closest('.portal-recruitment-history-table');
            if (!table) {
                return;
            }
            var requestId = summaryRow.dataset.requestId;
            if (!requestId) {
                return;
            }
            toggleDetail(table, requestId);
        });

        document.addEventListener('keydown', function (event) {
            var summaryRow = event.target.closest('.portal-recruitment-history-row');
            if (!summaryRow) {
                return;
            }
            if (event.key !== 'Enter' && event.key !== ' ') {
                return;
            }
            var table = summaryRow.closest('.portal-recruitment-history-table');
            if (!table) {
                return;
            }
            var requestId = summaryRow.dataset.requestId;
            if (!requestId) {
                return;
            }
            event.preventDefault();
            toggleDetail(table, requestId);
        });

        document.addEventListener('submit', function (event) {
            var filterForm = event.target.closest('.portal-recruitment-smart-filter');
            if (!filterForm) {
                return;
            }
            handleFilterFormSubmit(filterForm, event);
        });

        window.addEventListener('popstate', function () {
            fetchAndRender(getCurrentUrl(), { historyMode: 'none' });
        });
    }

    function init() {
        initEventDelegation();
        initTabState();
        restoreExpandedDetailState();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
