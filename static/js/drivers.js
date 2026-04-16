/**
 * Drivers Page JavaScript
 * This file handles interactive elements of the Drivers page.
 */

function toggleAllDetails(open) {
    document.querySelectorAll('details.interview-section').forEach(d => d.open = open);
}

// Additional common functions for the drivers page can go here.
console.log('Drivers JS loaded.');
