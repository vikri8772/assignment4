// A2: shows the chosen picture in the item form before it is saved.
// See docs/plans/a2-item-image-sequence.md. The server checks the file again on Save.

const MAX_SIZE = 5 * 1024 * 1024; // 5 MB
const TYPES = ["image/jpeg", "image/png"];

const input = document.getElementById("picture");
const newPicture = document.getElementById("picture-new");
const preview = document.getElementById("picture-preview");
const removeButton = document.getElementById("picture-remove");
const error = document.getElementById("picture-error");

function reset() {
  // Clears the chosen file and hides the preview. Nothing has been saved.
  input.value = "";
  newPicture.hidden = true;
  removeButton.hidden = true;
  if (preview.src) {
    URL.revokeObjectURL(preview.src);
    preview.removeAttribute("src");
  }
}

input.addEventListener("change", () => {
  error.textContent = "";
  const file = input.files[0];
  if (!file) {
    reset();
    return;
  }
  if (!TYPES.includes(file.type)) {
    reset();
    error.textContent = "Choose a JPG or PNG picture.";
    return;
  }
  if (file.size > MAX_SIZE) {
    reset();
    error.textContent = "The picture is larger than 5 MB. Choose a smaller one.";
    return;
  }
  if (preview.src) {
    URL.revokeObjectURL(preview.src);
  }
  preview.src = URL.createObjectURL(file);
  newPicture.hidden = false;
  removeButton.hidden = false;
});

removeButton.addEventListener("click", () => {
  error.textContent = "";
  reset();
});
