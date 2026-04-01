/** @odoo-module **/

import Fullscreen from '@website_slides/js/slides_course_fullscreen_player';

Fullscreen.include({
    events: Object.assign({}, Fullscreen.prototype.events, {
        'click .o_wslides_soc_mark_done': '_onClickMarkDone',
    }),

    /**
     * @override
     * Disable auto-completion for SOC slides
     */
    _preprocessSlideData: function (slidesDataList) {
        var slides = this._super.apply(this, arguments);
        slides.forEach(function (slide) {
            // Check if slide is SOC (requires data-is-soc in template)
            if (slide.isSoc) {
                slide._autoSetDone = false;
            }
        });
        return slides;
    },

    /**
     * Handle manual "Mark as Done" click
     */
    _onClickMarkDone: function (ev) {
        ev.preventDefault();
        var slide = this._slideValue;
        if (!slide.completed) {
            this._toggleSlideCompleted(slide, true);
        }
    }
});
