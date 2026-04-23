module.exports = {
  default: {
    paths: ["tests/bdd/features/**/*.feature"],
    import: ["tsx/esm"],
    require: ["tests/bdd/steps/**/*.ts", "tests/bdd/support/**/*.ts"],
    format: [
      "progress-bar",
      "json:test-results/cucumber.json",
      "message:test-results/cucumber.ndjson",
    ],
    formatOptions: { snippetInterface: "async-await" },
    strict: true,
    failFast: false,
    parallel: 0,
  },
};
