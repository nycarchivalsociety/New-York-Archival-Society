var TrandingSlider = new Swiper(".tranding-slider", {
  effect: "coverflow",
  grabCursor: true,
  centeredSlides: true,
  loop: true,
  slidesPerView: "auto",
  coverflowEffect: { rotate: 0, stretch: 0, depth: 100, modifier: 2.5 },
  pagination: { el: ".swiper-pagination", clickable: true },
  navigation: { nextEl: ".swiper-button-next", prevEl: ".swiper-button-prev" },
});

(function () {
  "use strict";

  const select = (el, all = false) => {
    if (!el || typeof el !== "string") return;
    el = el.trim();
    return all
      ? [...document.querySelectorAll(el)]
      : document.querySelector(el);
  };

  const on = (type, el, listener, all = false) => {
    let selectEl = select(el, all);
    if (selectEl) {
      if (all) {
        selectEl.forEach((e) => e.addEventListener(type, listener));
      } else {
        selectEl.addEventListener(type, listener);
      }
    }
  };

  document
    .querySelectorAll(".faq-item h3, .faq-item .faq-toggle")
    .forEach((faqItem) => {
      faqItem.addEventListener("click", () => {
        faqItem.parentNode.classList.toggle("faq-active");
      });
    });

  let navbarlinks = select("#navbar .scrollto", true);
  const navbarlinksActive = () => {
    let position = window.scrollY + 200;
    navbarlinks.forEach((navbarlink) => {
      if (!navbarlink.hash) return;
      let section = select(navbarlink.hash);
      if (!section) return;
      navbarlink.classList[
        position >= section.offsetTop &&
        position <= section.offsetTop + section.offsetHeight
          ? "add"
          : "remove"
      ]("active");
    });
  };

  const scrollto = (el) => {
    let offset = select("#header").offsetHeight;
    window.scrollTo({ top: select(el).offsetTop - offset, behavior: "smooth" });
  };

  const headerScrolled = () => {
    const scrolled = window.scrollY > 100;
    select("#header").classList[scrolled ? "add" : "remove"]("header-scrolled");
    select("#topbar")?.classList[scrolled ? "add" : "remove"](
      "topbar-scrolled"
    );
  };

  window.addEventListener("load", () => {
    navbarlinksActive();
    headerScrolled();

    if (window.location.hash && select(window.location.hash)) {
      scrollto(window.location.hash);
    }

    select("#preloader")?.remove();

    let menuContainer = select(".menu-container");
    if (menuContainer) {
      let menuIsotope = new Isotope(menuContainer, {
        itemSelector: ".menu-item",
        layoutMode: "fitRows",
      });
      let menuFilters = select("#menu-flters li", true);
      on(
        "click",
        "#menu-flters li",
        function (e) {
          e.preventDefault();
          menuFilters.forEach((el) => el.classList.remove("filter-active"));
          this.classList.add("filter-active");
          menuIsotope.arrange({ filter: this.getAttribute("data-filter") });
          menuIsotope.on("arrangeComplete", () => AOS.refresh());
        },
        true
      );
    }

    AOS.init({
      duration: 1000,
      easing: "ease-in-out",
      once: true,
      mirror: false,
    });
  });

  on("click", ".mobile-nav-toggle", function () {
    select("#navbar").classList.toggle("navbar-mobile");
    this.classList.toggle("bi-list");
    this.classList.toggle("bi-x");
  });

  on(
    "click",
    ".navbar .dropdown > a",
    function (e) {
      if (select("#navbar").classList.contains("navbar-mobile")) {
        e.preventDefault();
        this.nextElementSibling.classList.toggle("dropdown-active");
      }
    },
    true
  );

  on(
    "click",
    ".scrollto",
    function (e) {
      if (select(this.hash)) {
        e.preventDefault();
        let navbar = select("#navbar");
        if (navbar.classList.contains("navbar-mobile")) {
          navbar.classList.remove("navbar-mobile");
          let navbarToggle = select(".mobile-nav-toggle");
          navbarToggle.classList.toggle("bi-list");
          navbarToggle.classList.toggle("bi-x");
        }
        scrollto(this.hash);
      }
    },
    true
  );

  const glightbox = GLightbox({ selector: ".glightbox" });
  new Swiper(".events-slider", {
    speed: 600,
    loop: true,
    autoplay: { delay: 5000, disableOnInteraction: false },
    slidesPerView: "auto",
    pagination: { el: ".swiper-pagination", type: "bullets", clickable: true },
  });
  new Swiper(".testimonials-slider", {
    speed: 600,
    loop: true,
    autoplay: { delay: 5000, disableOnInteraction: false },
    slidesPerView: "auto",
    pagination: { el: ".swiper-pagination", type: "bullets", clickable: true },
    breakpoints: {
      320: { slidesPerView: 1, spaceBetween: 20 },
      1200: { slidesPerView: 3, spaceBetween: 20 },
    },
  });
  const galleryLightbox = GLightbox({ selector: ".gallery-lightbox" });

  window.addEventListener("scroll", () => {
    navbarlinksActive();
    headerScrolled();
  });
})();
