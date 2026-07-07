// Wishlist

function openWishlist() {
    document.getElementById("Wishlist").style.display = "block";
}
function closeWishlist() {
    document.getElementById("Wishlist").style.display = "none";
}

// Cart

function openCart() {
    document.getElementById("Cart").style.display = "block";
}
function closeCart() {
    document.getElementById("Cart").style.display = "none";
}

// Search

function openSearch() {
    document.getElementById("Search").style.display = "block";
}
function closeSearch() {
    document.getElementById("Search").style.display = "none";
}

// countdown

(function () {
    const second = 1000,
        minute = second * 60,
        hour = minute * 60,
        day = hour * 24;

    let birthday = "Oct 30, 2025 00:00:00",
        countDown = new Date(birthday).getTime();

    const daysEl = document.getElementById("days");
    const hoursEl = document.getElementById("hours");
    const minutesEl = document.getElementById("minutes");
    const secondsEl = document.getElementById("seconds");

    if (!daysEl || !hoursEl || !minutesEl || !secondsEl) return;

    const x = setInterval(function() {
        let now = new Date().getTime(),
            distance = countDown - now;

        daysEl.innerText = Math.floor(distance / day);
        hoursEl.innerText = Math.floor((distance % day) / hour);
        minutesEl.innerText = Math.floor((distance % hour) / minute);
        secondsEl.innerText = Math.floor((distance % minute) / second);

        if (distance < 0) {
            let headline = document.getElementById("headline"),
                countdown = document.getElementById("countdown"),
                content = document.getElementById("content");

            if (headline) headline.innerText = "It's my birthday!";
            if (countdown) countdown.style.display = "none";
            if (content) content.style.display = "block";

            clearInterval(x);
        }
    }, 1000);
})();