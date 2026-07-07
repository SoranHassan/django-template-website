$(function() {
    "use strict";

    // Loader
    function preloaderLoad() {
        if ($('.preloader').length) {
            $('.preloader').delay(200).fadeOut(300);
        }
        $(".preloader_disabler").on('click', function() {
            $("#preloader").hide();
        });
    }
    preloaderLoad();

    // Navigation Plugin
    (function($, window, document, undefined) {
        $.navigation = function(element, options) {
            const defaults = {
                responsive: true,
                mobileBreakpoint: 992,
                showDuration: 300,
                hideDuration: 300,
                showDelayDuration: 0,
                hideDelayDuration: 0,
                submenuTrigger: "hover", // or "click"
                effect: "fade", // or "slide"
                submenuIndicator: true,
                hideSubWhenGoOut: true,
                visibleSubmenusOnMobile: false,
                fixed: false,
                overlay: true,
                overlayColor: "rgba(0, 0, 0, 0.5)",
                hidden: false,
                offCanvasSide: "left", // or "right"
                onInit: function() {},
                onShowOffCanvas: function() {},
                onHideOffCanvas: function() {}
            };

            const nav = this;
            nav.settings = {};
            const $navElement = $(element);
            let lastWindowWidth = Number.MAX_VALUE;
            let currentWindowWidth = 1;

            // Append close button dynamically
            if ($navElement.find(".nav-menus-wrapper .nav-menus-wrapper-close-button").length === 0) {
                $navElement.find(".nav-menus-wrapper").prepend("<button class='nav-menus-wrapper-close-button border-0' aria-label='Close navigation'>✕</button>");
            }

            // If search form exists, add close button
            if ($navElement.find(".nav-search").length > 0 && $navElement.find(".nav-search .nav-search-close-button").length === 0) {
                $navElement.find(".nav-search form").prepend("<button class='nav-search-close-button' aria-label='Close search'>✕</button>");
            }

            nav.init = function() {
                nav.settings = $.extend({}, defaults, options);

                if (nav.settings.offCanvasSide === "right") {
                    $navElement.find(".nav-menus-wrapper").addClass("nav-menus-wrapper-right");
                }

                if (nav.settings.hidden) {
                    $navElement.addClass("navigation-hidden");
                    nav.settings.mobileBreakpoint = 99999; // force mobile mode always
                }

                if (nav.settings.fixed) {
                    $navElement.addClass("navigation-fixed");
                }

                nav.setupSubmenus();
                nav.bindEvents();
                nav.adjustLayout();

                $(window).resize(function() {
                    nav.adjustLayout();
                    nav.adjustSubmenuPosition();
                });

                nav.settings.onInit.call(element);
            };

            nav.setupSubmenus = function() {
                $navElement.find("li").each(function() {
                    const $this = $(this);
                    if ($this.children(".nav-dropdown, .megamenu-panel").length > 0) {
                        $this.children(".nav-dropdown, .megamenu-panel").addClass("nav-submenu");
                        if (nav.settings.submenuIndicator) {
                            $this.children("a").append("<span class='submenu-indicator'><span class='submenu-indicator-chevron'></span></span>");
                        }
                    }
                });
            };

            nav.showSubmenu = function($li, effect) {
                if (nav.getWindowWidth() > nav.settings.mobileBreakpoint) {
                    $navElement.find(".nav-search form").slideUp();
                }
                if (effect === "fade") {
                    $li.children(".nav-submenu").stop(true, true).delay(nav.settings.showDelayDuration).fadeIn(nav.settings.showDuration);
                } else {
                    $li.children(".nav-submenu").stop(true, true).delay(nav.settings.showDelayDuration).slideDown(nav.settings.showDuration);
                }
                $li.addClass("nav-submenu-open");
            };

            nav.hideSubmenu = function($li, effect) {
                if (effect === "fade") {
                    $li.find(".nav-submenu").stop(true, true).delay(nav.settings.hideDelayDuration).fadeOut(nav.settings.hideDuration);
                } else {
                    $li.find(".nav-submenu").stop(true, true).delay(nav.settings.hideDelayDuration).slideUp(nav.settings.hideDuration);
                }
                $li.removeClass("nav-submenu-open").find(".nav-submenu-open").removeClass("nav-submenu-open");
            };

            // Show offcanvas overlay and block scroll
            nav.showOffcanvasOverlay = function() {
                $("body").addClass("no-scroll");
                if (nav.settings.overlay) {
                    if ($navElement.find(".nav-overlay-panel").length === 0) {
                        $navElement.append("<div class='nav-overlay-panel'></div>");
                    }
                    $navElement.find(".nav-overlay-panel")
                        .css("background-color", nav.settings.overlayColor)
                        .fadeIn(300)
                        .on("click touchstart", function() {
                            nav.hideOffcanvas();
                        });
                }
            };

            // Hide offcanvas overlay and unblock scroll
            nav.hideOffcanvasOverlay = function() {
                $("body").removeClass("no-scroll");
                if (nav.settings.overlay) {
                    $navElement.find(".nav-overlay-panel").fadeOut(400, function() {
                        $(this).remove();
                    });
                }
            };

            nav.showOffcanvas = function() {
                nav.showOffcanvasOverlay();

                if (nav.settings.offCanvasSide === "left") {
                    $navElement.find(".nav-menus-wrapper").css("transition-property", "left").addClass("nav-menus-wrapper-open");
                } else {
                    $navElement.find(".nav-menus-wrapper").css("transition-property", "right").addClass("nav-menus-wrapper-open");
                }
            };

            nav.hideOffcanvas = function() {
                $navElement.find(".nav-menus-wrapper").removeClass("nav-menus-wrapper-open").on("webkitTransitionEnd moztransitionend transitionend oTransitionEnd", function() {
                    $(this).css("transition-property", "none").off();
                });
                nav.hideOffcanvasOverlay();
            };

            nav.toggleOffcanvas = function() {
                if (nav.getWindowWidth() <= nav.settings.mobileBreakpoint) {
                    if ($navElement.find(".nav-menus-wrapper").hasClass("nav-menus-wrapper-open")) {
                        nav.hideOffcanvas();
                    } else {
                        nav.showOffcanvas();
                    }
                }
            };

            nav.toggleSearch = function() {
                const $searchForm = $navElement.find(".nav-search form");
                if ($searchForm.css("display") === "none") {
                    $searchForm.slideDown();
                    $navElement.find(".nav-submenu").fadeOut(200);
                } else {
                    $searchForm.slideUp();
                }
            };

            nav.adjustLayout = function() {
                if (!nav.settings.responsive) {
                    nav.activateDesktopMenu();
                    return;
                }

                const width = nav.getWindowWidth();

                if (width <= nav.settings.mobileBreakpoint && lastWindowWidth > nav.settings.mobileBreakpoint) {
                    // Switch to mobile mode
                    $navElement.addClass("navigation-portrait").removeClass("navigation-landscape");
                    nav.activateMobileMenu();
                } else if (width > nav.settings.mobileBreakpoint && currentWindowWidth <= nav.settings.mobileBreakpoint) {
                    // Switch to desktop mode
                    $navElement.addClass("navigation-landscape").removeClass("navigation-portrait");
                    nav.activateDesktopMenu();
                    nav.hideOffcanvas();
                    nav.hideOffcanvasOverlay();
                }
                lastWindowWidth = width;
                currentWindowWidth = width;
            };

            nav.activateDesktopMenu = function() {
                nav.unbindMenuEvents();
                $navElement.find(".nav-submenu").hide();
                nav.bindHoverEvents();
                if (nav.settings.hideSubWhenGoOut) nav.bindBodyClick();
            };

            nav.activateMobileMenu = function() {
                nav.unbindMenuEvents();
                $navElement.find(".nav-submenu").hide();
                if (nav.settings.visibleSubmenusOnMobile) {
                    $navElement.find(".nav-submenu").show();
                }
                if (nav.settings.submenuIndicator) {
                    nav.bindSubmenuIndicatorClick();
                } else {
                    nav.bindClickEvents();
                }
            };

            nav.unbindMenuEvents = function() {
                $navElement.find(".nav-menu li, .nav-menu a").off("click.nav touchstart.nav mouseenter.nav mouseleave.nav");
                $("body").off("click.body touchstart.body");
            };

            nav.bindHoverEvents = function() {
                $navElement.find(".nav-menu li").on("mouseenter.nav", function() {
                    nav.showSubmenu($(this), nav.settings.effect);
                    nav.adjustSubmenuPosition();
                }).on("mouseleave.nav", function() {
                    nav.hideSubmenu($(this), nav.settings.effect);
                });
            };

            nav.bindClickEvents = function() {
                $navElement.find(".nav-menu, .nav-dropdown").children("li").children("a").on("click.nav touchstart.nav", function(e) {
                    const $this = $(this);
                    if ($this.siblings(".nav-submenu").length > 0) {
                        e.preventDefault();
                        e.stopPropagation();
                        if ($this.siblings(".nav-submenu").css("display") === "none") {
                            nav.hideSubmenu($this.parent("li").siblings("li"), nav.settings.effect);
                            nav.hideSubmenu($this.closest(".nav-menu").siblings(".nav-menu").children("li"), nav.settings.effect);
                            nav.showSubmenu($this.parent("li"), nav.settings.effect);
                            nav.adjustSubmenuPosition();
                        } else {
                            nav.hideSubmenu($this.parent("li"), nav.settings.effect);
                        }
                    }
                });
            };

            nav.bindSubmenuIndicatorClick = function() {
                $navElement.find(".submenu-indicator").on("click.nav touchstart.nav", function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    const $indicator = $(this);
                    const $parentLi = $indicator.parent("a").parent("li");

                    nav.hideSubmenu($parentLi.siblings("li"), "slide");
                    nav.hideSubmenu($parentLi.closest(".nav-menu").siblings(".nav-menu").children("li"), "slide");

                    if ($indicator.hasClass("submenu-indicator-up")) {
                        $indicator.removeClass("submenu-indicator-up");
                        nav.hideSubmenu($parentLi, "slide");
                    } else {
                        $navElement.find(".submenu-indicator").removeClass("submenu-indicator-up");
                        $indicator.addClass("submenu-indicator-up");
                        nav.showSubmenu($parentLi, "slide");
                    }
                });
            };

            nav.bindBodyClick = function() {
                $("body").on("click.body touchstart.body", function(e) {
                    if ($(e.target).closest(".navigation").length === 0) {
                        $navElement.find(".nav-submenu").fadeOut();
                        $navElement.find(".nav-submenu-open").removeClass("nav-submenu-open");
                        $navElement.find(".nav-search form").slideUp();
                    }
                });
            };

            nav.adjustSubmenuPosition = function() {
                if (nav.getWindowWidth() > nav.settings.mobileBreakpoint) {
                    const navOuterWidth = $navElement.outerWidth(true);
                    $navElement.find(".nav-menu").children("li").children(".nav-submenu").each(function() {
                        const $submenu = $(this);
                        const parentLeft = $submenu.parent().position().left;
                        const submenuWidth = $submenu.outerWidth();
                        if (parentLeft + submenuWidth > navOuterWidth) {
                            $submenu.css("right", 0);
                        } else {
                            $submenu.css("right", "auto");
                        }
                    });
                }
            };

            nav.getWindowWidth = function() {
                return window.innerWidth || document.documentElement.clientWidth || document.body.clientWidth;
            };

            nav.bindEvents = function() {
                // Toggle offcanvas
                $navElement.find(".nav-toggle").on("click touchstart", function(e) {
                    e.preventDefault();
                    nav.toggleOffcanvas();
                });

                // Close button in offcanvas
                $navElement.find(".nav-menus-wrapper-close-button").on("click touchstart", function(e) {
                    e.preventDefault();
                    nav.hideOffcanvas();
                });

                // Search open/close
                $navElement.find(".nav-search-button").on("click touchstart", function(e) {
                    e.preventDefault();
                    nav.toggleSearch();
                });
                $navElement.find(".nav-search-close-button").on("click touchstart", function(e) {
                    e.preventDefault();
                    nav.toggleSearch();
                });
            };

            nav.init();
        };

        $.fn.navigation = function(options) {
            return this.each(function() {
                if (undefined === $(this).data("navigation")) {
                    const navInstance = new $.navigation(this, options);
                    $(this).data("navigation", navInstance);
                }
            });
        };
    })(jQuery, window, document);

    // Initialize navigation on #navigation element
    $(document).ready(function() {
        $("#navigation").navigation();
    });

	
	// Product Preview
	$(document).ready(function() {
		$('.sp-wrap').smoothproducts();
	});


	// Range Slider Script
	$(document).ready(function () {
		$(".js-range-slider").ionRangeSlider({
			type: "double",
			min: 0,
			max: 1000,
			from: 100,
			to: 750,
			grid: true
		});
	});

	
	// Tooltip
	$(document).ready(function () {
		$('[data-toggle="tooltip"]').tooltip();
	});
	
	// Snackbar for Add To Cart Product
	$(document).ready(function () {
		$('.snackbar-addcart').on('click', function () {
			Snackbar.show({
			text: 'Your product was added to cart successfully!',
			pos: 'top-right',
			showAction: false,
			actionText: 'Dismiss',
			duration: 3000,
			textColor: '#fff',
			backgroundColor: '#151515'
			});
		});
	});
	
	// Snackbar for wishlist Product
	$(document).ready(function () {
		$('.snackbar-wishlist').on('click', function () {
			Snackbar.show({
			text: 'Your product was added to wishlist successfully!',
			pos: 'top-right',
			showAction: false,
			actionText: 'Dismiss',
			duration: 3000,
			textColor: '#fff',
			backgroundColor: '#151515'
			});
		});
	});
	
	// Bottom To Top Scroll Script
	$(document).ready(function () {
		$(window).on('scroll', function () {
			const scrollHeight = $(window).scrollTop();
			if (scrollHeight > 100) {
			$('#back2Top').fadeIn();
			} else {
			$('#back2Top').fadeOut();
			}
		});
	});
	
	
	// Script For Fix Header on Scroll
	$(document).ready(function () {
		$(window).on('scroll', function () {
			const scrollPosition = $(window).scrollTop();

			if (scrollPosition >= 50) {
			$('.header').addClass('header-fixed');
			} else {
			$('.header').removeClass('header-fixed');
			}
		});
	});

	
	$(document).ready(function () {
		// Brand-slide
		$('.smart-brand').slick({
			slidesToShow: 6,
			arrows: false,
			dots: false,
			infinite: true,
			autoplaySpeed: 2000,
			autoplay: true,
			responsive: [
				{
					breakpoint: 1024,
					settings: {
					slidesToShow: 4,
					arrows: false,
					dots: false,
					},
				},
				{
					breakpoint: 600,
					settings: {
					slidesToShow: 3,
					arrows: false,
					dots: false,
					},
				},
			],
		});

		// reviews-slide
		$('.reviews-slide').slick({
			slidesToShow: 1,
			arrows: true,
			dots: false,
			infinite: true,
			autoplaySpeed: 2000,
			autoplay: true,
			responsive: [
				{
					breakpoint: 1024,
					settings: {
					slidesToShow: 1,
					arrows: true,
					dots: false,
					},
				},
				{
					breakpoint: 600,
					settings: {
					slidesToShow: 1,
					arrows: true,
					dots: false,
					},
				},
			],
		});
	
		// quick_view_slide
		$('.quick_view_slide').slick({
			slidesToShow: 1,
			arrows: true,
			dots: true,
			infinite: true,
			autoplaySpeed: 2000,
			autoplay: true,
			responsive: [
				{
					breakpoint: 1024,
					settings: {
					slidesToShow: 1,
					arrows: true,
					dots: true,
					},
				},
				{
					breakpoint: 600,
					settings: {
					slidesToShow: 1,
					arrows: true,
					dots: true,
					},
				},
			],
		});
	
		// item Slide
		$('.slide_items').slick({
			slidesToShow: 4,
			arrows: true,
			dots: false,
			infinite: true,
			speed: 500,
			cssEase: 'linear',
			autoplaySpeed: 2000,
			autoplay: true,
			responsive: [
				{
					breakpoint: 1024,
					settings: {
					slidesToShow: 3,
					arrows: true,
					dots: false,
					},
				},
				{
					breakpoint: 600,
					settings: {
					slidesToShow: 1,
					arrows: true,
					dots: false,
					},
				},
			],
		});

		// Insta Slider
		$('.insta-slider').slick({
			slidesToShow: 8,
			infinite: true,
			slidesToScroll: 1,
			arrows: true,
			autoplay: true,
			autoplaySpeed: 3000,
			speed: 400,
			responsive: [
				{
					breakpoint: 1025,
					settings: {
					slidesToShow: 8,
					},
				},
				{
					breakpoint: 992,
					settings: {
					slidesToShow: 4,
					},
				},
				{
					breakpoint: 767,
					settings: {
					slidesToShow: 2,
					},
				},
			],
		});

	});
	

	$(document).ready(function () {
		const $slider = $('.home-slider');

		function applyInlineBackgrounds() {
			$slider.find('.item').each(function () {
			const $item = $(this);
			const imgBg = $item.data('background-image');
			const colorBg = $item.data('background-color');

			if (imgBg) {
				$item.css({
				"background-image": `url(${imgBg})`,
				"background-size": "cover",
				"background-position": "center center",
				"background-repeat": "no-repeat"
				});
			}

			if (colorBg) {
				$item.css("background", colorBg);
			}
			});
		}

		function manageSlideFocus() {
			const $slides = $slider.find('.slick-slide');
			const $activeSlide = $slides.filter('.slick-current.slick-active').first();
			const $focusedSlide = $(document.activeElement).closest('.slick-slide');

			if ($focusedSlide.length && !$activeSlide.is($focusedSlide)) {
			const $focusTarget = $activeSlide.find('a, button, input, select, textarea, [tabindex]:not([tabindex="-1"])').first();
			if ($focusTarget.length) {
				$focusTarget.focus();
			} else {
				$activeSlide.attr('tabindex', '-1').focus();
			}
			}

			$slides.each(function () {
			const $slide = $(this);
			const isActive = $slide.is($activeSlide);
			const containsFocus = $slide[0].contains(document.activeElement);

			if (isActive || containsFocus) {
				$slide.removeAttr('aria-hidden inert');
			} else {
				$slide.attr('aria-hidden', 'true').attr('inert', '');
			}
			});
		}

		$slider.on('init afterChange setPosition breakpoint', function () {
			applyInlineBackgrounds();
			setTimeout(manageSlideFocus, 30);
		});

		$slider.slick({
			centerMode: false,
			slidesToShow: 1,
			arrows: true,
			dots: true,
			accessibility: true,
			autoplay: true,
			autoplaySpeed: 2000,
			speed: 400,
			responsive: [
			{
				breakpoint: 768,
				settings: {
				slidesToShow: 1,
				arrows: true,
				}
			},
			{
				breakpoint: 480,
				settings: {
				slidesToShow: 1,
				arrows: true,
				}
			}
			]
		});

		// Failsafe: blur focus if it's inside a hidden slide
		setInterval(() => {
			const focused = document.activeElement;
			const $focusedSlide = $(focused).closest('.slick-slide[aria-hidden="true"]');
			if ($focusedSlide.length) {
			focused.blur();
			}
		}, 200);
	});

});