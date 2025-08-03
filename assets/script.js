function toggleAccordion(clickedAccordion) {
    var currentContentHeight = window.getComputedStyle(clickedAccordion.parentElement.getElementsByClassName('accordion-element-content')[0]).height;
    // close clicked accordion
    if (currentContentHeight != '0px') {
        clickedAccordion.parentElement.getElementsByClassName('accordion-element-content')[0].style.height = '0px';
        clickedAccordion.style.backgroundColor = '';
        clickedAccordion.getElementsByClassName('expand-collapse-icon')[0].textContent = '+';
    }
    // open clicked accordion and close all other accordions
    else {
        var accordionElements = document.getElementsByClassName('accordion-element');
        Array.from(accordionElements).forEach(function(element) {
            title = element.getElementsByClassName('accordion-element-title')[0];
            content = element.getElementsByClassName('accordion-element-content')[0];
            if (title == clickedAccordion) {
                title.style.backgroundColor = 'lightgrey';
                content.style.height =  content.scrollHeight + 'px';
                title.getElementsByClassName('expand-collapse-icon')[0].textContent = '–';
            }
            else {
                title.style.backgroundColor = '';
                content.style.height = '0px';
                title.getElementsByClassName('expand-collapse-icon')[0].textContent = '+';
            }
        });
    }
}

window.addEventListener('click', function(event) {
    const clickedElement = event.target;
    if (clickedElement.classList.contains('accordion-element-title')) {
        toggleAccordion(clickedElement);
    }
});