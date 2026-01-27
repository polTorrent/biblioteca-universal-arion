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
   REDISSENY v2 - Carrousel i Cercador
   ═══════════════════════════════════════════════════════════════════ */

/**
 * Gestió del carrousel d'obres
 */
class CarouselManager {
    constructor() {
        this.track = document.querySelector('.carousel-track');
        this.prevBtn = document.querySelector('.nav-arrow.prev');
        this.nextBtn = document.querySelector('.nav-arrow.next');
        this.cards = document.querySelectorAll('.work-card-carousel');

        if (!this.track || this.cards.length === 0) return;

        this.currentIndex = 0;
        this.itemsPerView = this.getItemsPerView();
        this.maxIndex = Math.max(0, this.cards.length - this.itemsPerView);

        this.init();
    }

    init() {
        if (this.prevBtn) {
            this.prevBtn.addEventListener('click', () => this.slide(-1));
        }
        if (this.nextBtn) {
            this.nextBtn.addEventListener('click', () => this.slide(1));
        }

        // Recalcular en resize
        window.addEventListener('resize', () => {
            this.itemsPerView = this.getItemsPerView();
            this.maxIndex = Math.max(0, this.cards.length - this.itemsPerView);
            this.currentIndex = Math.min(this.currentIndex, this.maxIndex);
            this.updatePosition();
            this.updateButtons();
        });

        this.updateButtons();
    }

    getItemsPerView() {
        const width = window.innerWidth;
        if (width > 1200) return 5;
        if (width > 1024) return 4;
        if (width > 768) return 3;
        if (width > 480) return 2;
        return 1;
    }

    slide(direction) {
        this.currentIndex = Math.max(0, Math.min(this.maxIndex, this.currentIndex + direction));
        this.updatePosition();
        this.updateButtons();
    }

    updatePosition() {
        if (!this.cards[0]) return;

        const cardWidth = this.cards[0].offsetWidth;
        const gap = parseInt(getComputedStyle(this.track).gap) || 24;
        const offset = -this.currentIndex * (cardWidth + gap);

        this.track.style.transform = `translateX(${offset}px)`;
    }

    updateButtons() {
        if (this.prevBtn) {
            this.prevBtn.disabled = this.currentIndex === 0;
        }
        if (this.nextBtn) {
            this.nextBtn.disabled = this.currentIndex >= this.maxIndex;
        }
    }
}

/**
 * Gestió del cercador expandible
 */
class SearchManager {
    constructor() {
        this.container = document.querySelector('.search-container');
        this.toggle = document.querySelector('.search-toggle');
        this.form = document.querySelector('.search-form');
        this.input = document.querySelector('.search-form input');

        if (!this.container || !this.toggle) return;

        this.init();
    }

    init() {
        // Toggle cercador en mòbil
        this.toggle.addEventListener('click', (e) => {
            e.preventDefault();
            this.container.classList.toggle('active');
            if (this.container.classList.contains('active') && this.input) {
                this.input.focus();
            }
        });

        // Tancar amb Escape
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.container.classList.contains('active')) {
                this.container.classList.remove('active');
            }
        });

        // Tancar si es clica fora
        document.addEventListener('click', (e) => {
            if (!this.container.contains(e.target) && this.container.classList.contains('active')) {
                this.container.classList.remove('active');
            }
        });
    }
}

// Inicialitzar components v2
document.addEventListener('DOMContentLoaded', () => {
    new CarouselManager();
    new SearchManager();
});
