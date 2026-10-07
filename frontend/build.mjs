import {copyFileSync, mkdirSync} from 'node:fs';
mkdirSync('static/vendor', {recursive: true});
copyFileSync('node_modules/chart.js/dist/chart.umd.js', 'static/vendor/chart.js');
copyFileSync('node_modules/chart.js/dist/chart.umd.js.map', 'static/vendor/chart.umd.js.map');
copyFileSync('node_modules/htmx.org/dist/htmx.min.js', 'static/vendor/htmx.js');
copyFileSync('frontend/app.js', 'static/vendor/app.js');
