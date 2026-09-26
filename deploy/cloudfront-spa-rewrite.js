// CloudFront Function - viewer request event, cloudfront-js-2.0 runtime.
//
// Attach this ONLY to the default (S3 frontend) cache behavior, never to
// /api/*. React Router handles routes like /dashboard or /trade entirely
// in the browser - there's no actual /dashboard file in the S3 bucket.
// Without this, refreshing the page on one of those routes asks S3 for a
// file that doesn't exist and gets a 404. This rewrites any request for a
// path that isn't a real file (no extension, e.g. .js or .css) to
// /index.html instead, so the app's own JavaScript loads and React Router
// takes over from there.
function handler(event) {
  var request = event.request;
  var uri = request.uri;

  var lastSegment = uri.split("/").pop();
  var looksLikeAFile = lastSegment.includes(".");

  if (!looksLikeAFile) {
    request.uri = "/index.html";
  }

  return request;
}
