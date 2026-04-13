# Daily Brief Branding Guidelines

## CSS Styling for Daily Brief Email

```css
/* New York Times-inspired accessible design */
body {
  margin: 0;
  padding: 0;
  background: #ffffff;
  font-family: 'Times New Roman', Times, serif;
  color: #000000;
  line-height: 1.6;
}

.wrap {
  max-width: 850px;
  margin: 0 auto;
  padding: 10px;
  background: #ffffff;
}

/* Header section - compact */
.hero {
  border-bottom: 1px solid #cccccc;
  padding-bottom: 6px;
  margin-bottom: 10px;
  text-align: center;
}

.hero-title {
  font-size: 24px;
  font-weight: normal;
  color: #000000;
  margin: 0 0 3px 0;
  font-family: 'Times New Roman', Times, serif;
}

.hero-sub {
  color: #666666;
  font-size: 12px;
  font-style: italic;
  margin: 0;
}

/* Section headers */
.card {
  margin-bottom: 12px;
  border-bottom: 1px solid #dddddd;
  padding-bottom: 6px;
}


/* Stock ticker - single-line professional ticker style */
.stock-ticker-wrap {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 12px;
}

.stock-ticker {
  background: linear-gradient(90deg, #1a1a1a 0%, #2a2a2a 50%, #1a1a1a 100%);
  border: 2px solid #333333;
  justify-content: center;
  border-radius: 8px;
  padding: 6px 8px;
  margin-bottom: 0;
  font-family: 'Courier New', monospace;
  display: flex;
  flex-wrap: nowrap;
  align-items: center;
  overflow-x: auto;
}

.stock-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex-shrink: 0;
}

.stock-top {
  display: flex;
  align-items: center;
  gap: 5px;
}

.stock-bot {
  display: flex;
  align-items: center;
  gap: 3px;
  margin-top: 2px;
}

.stock-symbol {
  font-weight: bold;
  color: #ffffff;
  font-size: 11px;
  text-shadow: 0 0 5px rgba(255,255,255,0.5);
  font-family: 'Courier New', monospace;
}

.stock-price {
  color: #ffffff;
  font-size: 11px;
  font-weight: bold;
  font-family: 'Courier New', monospace;
}

.stock-change-label {
  color: #aaaaaa;
  font-size: 9px;
  font-family: 'Courier New', monospace;
}

.stock-change {
  font-size: 10px;
  font-weight: bold;
  font-family: 'Courier New', monospace;
}

.stock-change.positive {
  color: #00ff00;
  text-shadow: 0 0 5px rgba(0,255,0,0.5);
}

.stock-change.negative {
  color: #ff4444;
  text-shadow: 0 0 5px rgba(255,68,68,0.5);
}

.stock-sep {
  color: #555555;
  margin: 0 5px;
  font-family: 'Courier New', monospace;
  flex-shrink: 0;
}

.stock-sep-inner {
  color: #555555;
  font-family: 'Courier New', monospace;
}

/* News sections - 3-column newspaper layout */
.news-container {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  column-gap: 12px;
  row-gap: 0;
  margin-bottom: 6px;
  align-items: start;
}

.news-column {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.news-section {
  border: 1px solid #cccccc;
  border-radius: 6px;
  padding: 10px 12px;
  margin-bottom: 0;
  background: #ffffff;
}

.sec-label {
  font-size: 13px;
  font-weight: bold;
  color: #000000;
  margin: 0 0 8px 0;
  padding: 0 0 5px 0;
  border-bottom: 1px solid #dddddd;
  text-align: left;
  text-transform: none;
  letter-spacing: normal;
}

.news-item {
  margin-bottom: 4px;
  line-height: 1.1;
}

.news-item:last-child {
  margin-bottom: 0;
}

.news-title a {
  color: #000000;
  text-decoration: none;
  font-size: 13px;
  font-weight: normal;
  line-height: 1.1;
  display: block;
  margin-bottom: 0px;
}

.news-title a:hover {
  text-decoration: underline;
}

.news-desc {
  color: #666666;
  font-size: 12px;
  line-height: 1.1;
  margin-left: 0px;
  display: block;
}

.news-sub {
  color: #666666;
  font-size: 11px;
  font-style: italic;
  line-height: 1.2;
  margin-top: 2px;
}

/* Footer - compact */
.footer {
  text-align: center;
  color: #666666;
  font-size: 11px;
  margin-top: 12px;
  padding-top: 8px;
  border-top: 1px solid #cccccc;
  line-height: 1.4;
}

.footer a {
  color: #000000;
  text-decoration: underline;
}

/* Responsive design */
@media (max-width: 768px) {
  .wrap {
    padding: 15px;
  }

  .hero-title {
    font-size: 24px;
  }

  .news-container {
    grid-template-columns: 1fr;
    gap: 20px;
  }

  table {
    font-size: 12px;
  }

  td, th {
    padding: 6px 8px;
  }

  .news-title a {
    font-size: 13px;
  }

  .news-desc {
    font-size: 12px;
  }
}

/* Focus states for keyboard navigation */
a:focus {
  outline: 2px solid #000000;
  outline-offset: 2px;
}

/* High contrast mode support */
@media (prefers-contrast: high) {
  body {
    background: #ffffff;
    color: #000000;
  }

  .up {
    color: #000000;
    text-decoration: underline;
  }

  .dn {
    color: #000000;
    text-decoration: underline;
  }
}
```

## Design Principles

- **New York Times-inspired**: Clean, serif typography with Times New Roman
- **Accessible**: High contrast, focus states, semantic HTML
- **Responsive**: Mobile-friendly with grid layout
- **Professional**: Subtle colors, proper spacing, clean typography
- **Compact**: Efficient use of space for email readability

## Color Palette

- **Primary text**: #000000 (black)
- **Secondary text**: #666666 (gray)
- **Borders**: #cccccc, #dddddd, #e0e0e0
- **Backgrounds**: #ffffff (white), #f8f8f8 (light gray)

## Typography

- **Headers**: Times New Roman, normal weight
- **Body**: Times New Roman, 1.6 line height
- **Links**: Black with underline on hover
- **Responsive**: Scales appropriately for mobile

## Usage

This CSS should be included in the `<style>` tag of the HTML email template. Update this file whenever the newsletter design changes, and the code will automatically use the latest styling.