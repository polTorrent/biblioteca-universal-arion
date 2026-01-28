/**
 * ═══════════════════════════════════════════════════════════════════
 * EDITORIAL CLÀSSICA - APP.JS
 * JavaScript interactiu per a traduccions bilingües
 * ═══════════════════════════════════════════════════════════════════
 */

class EditorialClassica {
    constructor() {
        this.currentMode = localStorage.getItem('viewMode') || 'bilingue';
        this.theme = localStorage.getItem('theme') || 'light';
        this.syncScrollEnabled = true;

        this.init();
    }

    /**
     * Inicialització
     */
    init() {
        document.addEventListener('DOMContentLoaded', () => {
            this.initTheme();
            this.initViewControls();
            this.initTermTooltips();
            this.initSmoothScroll();
            this.initSyncScroll();
            this.highlightTargetOnLoad();
        });
    }

    /**
     * ─────────────────────────────────────────────────────────────────────
     * TEMA (MODE CLAR/FOSC)
     * ─────────────────────────────────────────────────────────────────────
     */
    initTheme() {
        // Aplicar tema guardat
        if (this.theme === 'dark') {
            document.documentElement.setAttribute('data-theme', 'dark');
        }

        // Botó de canvi de tema
        const themeToggle = document.querySelector('.theme-toggle');
        if (themeToggle) {
            this.updateThemeIcon(themeToggle);
            themeToggle.addEventListener('click', () => this.toggleTheme());
        }
    }

    toggleTheme() {
        this.theme = this.theme === 'light' ? 'dark' : 'light';
        localStorage.setItem('theme', this.theme);

        if (this.theme === 'dark') {
            document.documentElement.setAttribute('data-theme', 'dark');
        } else {
            document.documentElement.removeAttribute('data-theme');
        }

        const themeToggle = document.querySelector('.theme-toggle');
        if (themeToggle) {
            this.updateThemeIcon(themeToggle);
        }
    }

    updateThemeIcon(button) {
        button.innerHTML = this.theme === 'dark' ? '☀️' : '🌙';
        button.setAttribute('aria-label',
            this.theme === 'dark' ? 'Canviar a mode clar' : 'Canviar a mode fosc'
        );
    }

    /**
     * ─────────────────────────────────────────────────────────────────────
     * CONTROLS DE VISTA (ORIGINAL/BILINGÜE/TRADUCCIÓ)
     * ─────────────────────────────────────────────────────────────────────
     */
    initViewControls() {
        const container = document.querySelector('.text-container');
        if (!container) return;

        // Aplicar mode guardat
        container.setAttribute('data-mode', this.currentMode);

        // Actualitzar botons actius
        this.updateActiveButton();

        // Event listeners per botons
        const buttons = document.querySelectorAll('.view-btn');
        buttons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const mode = e.target.getAttribute('data-mode');
                this.setViewMode(mode);
            });
        });
    }

    setViewMode(mode) {
        this.currentMode = mode;
        localStorage.setItem('viewMode', mode);

        const container = document.querySelector('.text-container');
        if (container) {
            container.setAttribute('data-mode', mode);
        }

        this.updateActiveButton();
    }

    updateActiveButton() {
        const buttons = document.querySelectorAll('.view-btn');
        buttons.forEach(btn => {
            btn.classList.remove('active');
            if (btn.getAttribute('data-mode') === this.currentMode) {
                btn.classList.add('active');
            }
        });
    }

    /**
     * ─────────────────────────────────────────────────────────────────────
     * TOOLTIPS PER TERMES DEL GLOSSARI
     * ─────────────────────────────────────────────────────────────────────
     */
    initTermTooltips() {
        const terms = document.querySelectorAll('.term[data-term]');

        terms.forEach(term => {
            // Crear tooltip
            const tooltip = this.createTooltip(term);
            if (tooltip) {
                term.appendChild(tooltip);
            }

            // Events
            term.addEventListener('mouseenter', () => this.showTooltip(term));
            term.addEventListener('mouseleave', () => this.hideTooltip(term));
            term.addEventListener('focus', () => this.showTooltip(term));
            term.addEventListener('blur', () => this.hideTooltip(term));
        });
    }

    createTooltip(term) {
        const termId = term.getAttribute('data-term');
        const glossaryEntry = document.querySelector(`#term-${termId}`);

        if (!glossaryEntry) return null;

        const greek = glossaryEntry.querySelector('.term-greek');
        const translation = glossaryEntry.querySelector('.term-translation');

        if (!greek) return null;

        const tooltip = document.createElement('span');
        tooltip.className = 'term-tooltip';
        tooltip.innerHTML = `
            <span class="term-tooltip-greek">${greek.textContent}</span>
            ${translation ? `<br><span class="term-tooltip-trans">${translation.textContent.replace('Traducció:', '').trim()}</span>` : ''}
        `;

        return tooltip;
    }

    showTooltip(term) {
        const tooltip = term.querySelector('.term-tooltip');
        if (tooltip) {
            tooltip.classList.add('visible');
        }
    }

    hideTooltip(term) {
        const tooltip = term.querySelector('.term-tooltip');
        if (tooltip) {
            tooltip.classList.remove('visible');
        }
    }

    /**
     * ─────────────────────────────────────────────────────────────────────
     * SMOOTH SCROLL PER ANCRES
     * ─────────────────────────────────────────────────────────────────────
     */
    initSmoothScroll() {
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', (e) => {
                const targetId = anchor.getAttribute('href');
                if (targetId === '#') return;

                const target = document.querySelector(targetId);
                if (target) {
                    e.preventDefault();

                    // Offset per header sticky
                    const headerHeight = document.querySelector('.site-header')?.offsetHeight || 0;
                    const targetPosition = target.getBoundingClientRect().top + window.pageYOffset - headerHeight - 20;

                    window.scrollTo({
                        top: targetPosition,
                        behavior: 'smooth'
                    });

                    // Focus per accessibilitat
                    target.setAttribute('tabindex', '-1');
                    target.focus({ preventScroll: true });

                    // Actualitzar URL
                    history.pushState(null, null, targetId);
                }
            });
        });
    }

    /**
     * ─────────────────────────────────────────────────────────────────────
     * SCROLL SINCRONITZAT ENTRE COLUMNES
     * ─────────────────────────────────────────────────────────────────────
     */
    initSyncScroll() {
        const originalCol = document.querySelector('.original-column');
        const translationCol = document.querySelector('.translation-column');

        if (!originalCol || !translationCol) return;

        // Crear IntersectionObserver per detectar seccions visibles
        const sections = document.querySelectorAll('.section[data-parallel]');

        if (sections.length === 0) return;

        const observer = new IntersectionObserver((entries) => {
            if (!this.syncScrollEnabled) return;

            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const parallelId = entry.target.getAttribute('data-parallel');
                    const parallelSection = document.getElementById(parallelId);

                    if (parallelSection) {
                        // Highlight visual
                        this.highlightSection(entry.target);
                        this.highlightSection(parallelSection);
                    }
                }
            });
        }, {
            threshold: 0.5,
            rootMargin: '-100px 0px -100px 0px'
        });

        sections.forEach(section => observer.observe(section));
    }

    highlightSection(section) {
        // Treure highlight anterior
        document.querySelectorAll('.section.highlight').forEach(s => {
            s.classList.remove('highlight');
        });

        // Afegir highlight nou
        section.classList.add('highlight');

        // Treure després d'un temps
        setTimeout(() => {
            section.classList.remove('highlight');
        }, 2000);
    }

    /**
     * ─────────────────────────────────────────────────────────────────────
     * HIGHLIGHT TARGET ON LOAD
     * ─────────────────────────────────────────────────────────────────────
     */
    highlightTargetOnLoad() {
        if (window.location.hash) {
            const target = document.querySelector(window.location.hash);
            if (target) {
                setTimeout(() => {
                    const headerHeight = document.querySelector('.site-header')?.offsetHeight || 0;
                    const targetPosition = target.getBoundingClientRect().top + window.pageYOffset - headerHeight - 20;

                    window.scrollTo({
                        top: targetPosition,
                        behavior: 'smooth'
                    });
                }, 100);
            }
        }
    }

    /**
     * ─────────────────────────────────────────────────────────────────────
     * UTILITATS PÚBLIQUES
     * ─────────────────────────────────────────────────────────────────────
     */

    /**
     * Exportar text pla
     */
    exportAsText() {
        const content = document.querySelector('.translation-column');
        if (!content) {
            alert('No hi ha contingut per exportar');
            return;
        }

        const text = content.innerText;
        const title = document.querySelector('.work-title')?.textContent || 'traducció';

        const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
        const url = URL.createObjectURL(blob);

        const a = document.createElement('a');
        a.href = url;
        a.download = `${title.toLowerCase().replace(/\s+/g, '-')}.txt`;
        a.click();

        URL.revokeObjectURL(url);
    }

    /**
     * Compartir obra
     */
    shareWork() {
        const title = document.querySelector('.work-title')?.textContent || 'Obra';
        const url = window.location.href;

        if (navigator.share) {
            navigator.share({
                title: title,
                text: `Llegeix "${title}" a Editorial Clàssica`,
                url: url
            }).catch(console.error);
        } else {
            // Fallback: copiar URL
            navigator.clipboard.writeText(url).then(() => {
                alert('Enllaç copiat al porta-retalls');
            }).catch(() => {
                prompt('Copia aquest enllaç:', url);
            });
        }
    }

    /**
     * Imprimir
     */
    printWork() {
        window.print();
    }
}

// Inicialitzar
window.editorialClassica = new EditorialClassica();


/**
 * ═══════════════════════════════════════════════════════════════════
 * FUNCIONS AUXILIARS GLOBALS
 * ═══════════════════════════════════════════════════════════════════
 */

/**
 * Generar TOC automàtica
 */
function generateTOC() {
    const content = document.querySelector('.work-content, .text-container');
    const tocContainer = document.querySelector('.toc-list');

    if (!content || !tocContainer) return;

    const headings = content.querySelectorAll('h2, h3, .section-title');

    if (headings.length === 0) return;

    const toc = document.createElement('ul');
    toc.className = 'toc-items';

    headings.forEach((heading, index) => {
        // Assegurar que té ID
        if (!heading.id) {
            heading.id = `section-${index + 1}`;
        }

        const li = document.createElement('li');
        li.className = heading.tagName === 'H3' ? 'toc-item-sub' : 'toc-item';

        const a = document.createElement('a');
        a.href = `#${heading.id}`;
        a.textContent = heading.textContent;

        li.appendChild(a);
        toc.appendChild(li);
    });

    tocContainer.appendChild(toc);
}

// Generar TOC quan el document estigui llest
document.addEventListener('DOMContentLoaded', generateTOC);

/* ═══════════════════════════════════════════════════════════════════
   REDISSENY v2 - Carrusel i Cerca
   ═══════════════════════════════════════════════════════════════════ */

/**
 * Gestió del carrusel d'obres (suporta múltiples carrusels)
 */
class CarouselManager {
    constructor(carouselEl, navEl) {
        if (!carouselEl) return;

        this.carousel = carouselEl;
        this.track = carouselEl.querySelector('.carousel-track');
        this.cards = carouselEl.querySelectorAll('.work-card-carousel');

        if (!this.track || this.cards.length === 0) return;

        this.prevBtn = navEl ? navEl.querySelector('.nav-arrow.prev') : null;
        this.nextBtn = navEl ? navEl.querySelector('.nav-arrow.next') : null;
        this.currentOffset = 0;

        this.bindEvents();
        this.updateButtons();
    }

    bindEvents() {
        const self = this;

        if (this.prevBtn) {
            this.prevBtn.addEventListener('click', function() {
                self.slide(-1);
            });
        }
        if (this.nextBtn) {
            this.nextBtn.addEventListener('click', function() {
                self.slide(1);
            });
        }

        window.addEventListener('resize', function() {
            self.currentOffset = Math.min(self.currentOffset, self.getMaxOffset());
            self.updatePosition();
            self.updateButtons();
        });
    }

    getCardStep() {
        if (!this.cards[0]) return 200;
        const cardWidth = this.cards[0].offsetWidth;
        const style = window.getComputedStyle(this.track);
        const gap = parseInt(style.gap) || parseInt(style.columnGap) || 24;
        return cardWidth + gap;
    }

    getMaxOffset() {
        const trackWidth = this.track.scrollWidth;
        const visibleWidth = this.carousel.offsetWidth;
        return Math.max(0, trackWidth - visibleWidth);
    }

    slide(direction) {
        const step = this.getCardStep();
        const maxOffset = this.getMaxOffset();

        this.currentOffset = this.currentOffset + (direction * step);
        this.currentOffset = Math.max(0, Math.min(maxOffset, this.currentOffset));

        this.updatePosition();
        this.updateButtons();
    }

    updatePosition() {
        this.track.style.transform = 'translateX(-' + this.currentOffset + 'px)';
    }

    updateButtons() {
        if (this.prevBtn) {
            this.prevBtn.disabled = this.currentOffset <= 0;
        }
        if (this.nextBtn) {
            this.nextBtn.disabled = this.currentOffset >= this.getMaxOffset();
        }
    }
}

/**
 * Inicialitza tots els carrusels de la pàgina
 */
function initAllCarousels() {
    // Trobar totes les seccions amb carrusels
    var sections = document.querySelectorAll('.latest-works, .crowdfunding-section');

    sections.forEach(function(section) {
        var carousel = section.querySelector('.works-carousel');
        var prevBtn = section.querySelector('.nav-arrow.prev');
        var nextBtn = section.querySelector('.nav-arrow.next');

        if (!carousel) return;

        var track = carousel.querySelector('.carousel-track');
        var cards = carousel.querySelectorAll('.work-card-carousel');

        if (!track || cards.length === 0) return;

        var currentOffset = 0;

        function getCardStep() {
            if (!cards[0]) return 200;
            var cardWidth = cards[0].offsetWidth;
            var style = window.getComputedStyle(track);
            var gap = parseInt(style.gap) || parseInt(style.columnGap) || 24;
            return cardWidth + gap;
        }

        function getMaxOffset() {
            return Math.max(0, track.scrollWidth - carousel.offsetWidth);
        }

        function updatePosition() {
            track.style.transform = 'translateX(-' + currentOffset + 'px)';
        }

        function updateButtons() {
            if (prevBtn) prevBtn.disabled = currentOffset <= 0;
            if (nextBtn) nextBtn.disabled = currentOffset >= getMaxOffset();
        }

        function slide(direction) {
            var step = getCardStep();
            var maxOffset = getMaxOffset();
            currentOffset = currentOffset + (direction * step);
            currentOffset = Math.max(0, Math.min(maxOffset, currentOffset));
            updatePosition();
            updateButtons();
        }

        if (prevBtn) {
            prevBtn.addEventListener('click', function() { slide(-1); });
        }
        if (nextBtn) {
            nextBtn.addEventListener('click', function() { slide(1); });
        }

        window.addEventListener('resize', function() {
            currentOffset = Math.min(currentOffset, getMaxOffset());
            updatePosition();
            updateButtons();
        });

        updateButtons();
    });
}

/**
 * Gestió del panell de cerca desplegable
 */
class SearchPanelManager {
    constructor() {
        this.searchBtn = document.querySelector('.search-btn');
        this.searchPanel = document.querySelector('.search-panel');
        this.closeBtn = document.querySelector('.search-close');
        this.input = this.searchPanel?.querySelector('input');

        if (!this.searchBtn || !this.searchPanel) return;

        this.init();
    }

    init() {
        // Obrir panell amb botó de cerca
        this.searchBtn.addEventListener('click', (e) => {
            e.preventDefault();
            this.toggle();
        });

        // Tancar amb botó X
        if (this.closeBtn) {
            this.closeBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.close();
            });
        }

        // Tancar amb Escape
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isOpen()) {
                this.close();
            }
        });
    }

    isOpen() {
        return !this.searchPanel.hasAttribute('hidden');
    }

    toggle() {
        if (this.isOpen()) {
            this.close();
        } else {
            this.open();
        }
    }

    open() {
        this.searchPanel.removeAttribute('hidden');
        if (this.input) {
            this.input.focus();
        }
    }

    close() {
        this.searchPanel.setAttribute('hidden', '');
    }
}

/**
 * How Section - Accordion/Timeline
 */
function initHowSteps() {
    var steps = document.querySelectorAll('.how-step');
    if (!steps.length) return;

    function closeAll() {
        for (var i = 0; i < steps.length; i++) {
            steps[i].classList.remove('is-open');
            var btn = steps[i].querySelector('.how-step-header');
            if (btn) btn.setAttribute('aria-expanded', 'false');
        }
    }

    for (var i = 0; i < steps.length; i++) {
        (function(step) {
            var btn = step.querySelector('.how-step-header');
            if (!btn) return;

            btn.addEventListener('click', function(e) {
                e.preventDefault();
                var wasOpen = step.classList.contains('is-open');
                closeAll();
                if (!wasOpen) {
                    step.classList.add('is-open');
                    btn.setAttribute('aria-expanded', 'true');
                }
            });
        })(steps[i]);
    }

    // Tancar al clicar fora (només desktop)
    document.addEventListener('click', function(e) {
        if (window.innerWidth >= 768 && !e.target.closest('.how-step')) {
            closeAll();
        }
    });
}

// Inicialitzar components v2
document.addEventListener('DOMContentLoaded', function() {
    initAllCarousels();
    new SearchPanelManager();
    initHowSteps();
});
