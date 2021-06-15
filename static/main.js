<script src="https://cdn.jsdelivr.net/npm/flatpickr"></script>

      <script>
        // commonjs
        const flatpickr = require("flatpickr");

        // es modules are recommended, if available, especially for typescript
        import flatpickr from "flatpickr";

        flatpickr(".cal", { enableTime: true, dateFormat: "Y-m-d H:i" });
      </script>