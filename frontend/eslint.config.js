import js from "@eslint/js";
import lit from "eslint-plugin-lit";
import tseslint from "typescript-eslint";

export default tseslint.config(
  { ignores: ["node_modules"] },
  js.configs.recommended,
  ...tseslint.configs.strictTypeChecked,
  lit.configs["flat/recommended"],
  {
    languageOptions: {
      parserOptions: { projectService: true, tsconfigRootDir: import.meta.dirname },
    },
    rules: {
      // Lit binds template event listeners to the host element.
      "@typescript-eslint/unbound-method": "off",
    },
  },
  { files: ["*.js"], ...tseslint.configs.disableTypeChecked },
);
