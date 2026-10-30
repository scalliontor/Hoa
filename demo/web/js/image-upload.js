// ImageUpload (model view, A06 presentation layer): takes the customer's photo — from the upload button, a
// drop anywhere on the page, a paste or the camera — turns it into a JPEG and shows it as a preview card.
import { esc, MAX_UPLOAD_BYTES, toast, toJpeg } from "./core.js";

const ALLOWED_TYPES = ["image/jpeg", "image/png", "image/webp"];

export const ImageUpload = {
  file: null,      // the photo ready to send (always a JPEG of at most 1600 px)
  dataUrl: null,   // the same photo as a data URL

  /** Converts the photo, validates it and shows the preview card. Returns false if it cannot be used. */
  async choose(file) {
    if (!file) return false;
    let photo;
    try {
      photo = await toJpeg(file);
    } catch (error) {
      toast("We can't open this file — please choose a JPEG or PNG photo", true);
      return false;
    }
    if (!this.validate(photo.file)) return false;
    this.file = photo.file;
    this.dataUrl = photo.dataUrl;
    this.preview();
    return true;
  },

  /** NFR03: JPEG, PNG or WebP of at most 5 MB (checked after the conversion). The server checks again. */
  validate(file) {
    if (!ALLOWED_TYPES.includes(file.type)) {
      toast("We can't open this file — please choose a JPEG or PNG photo", true);
      return false;
    }
    if (file.size > MAX_UPLOAD_BYTES) {
      toast("This photo is still larger than 5 MB — please choose a smaller one", true);
      return false;
    }
    return true;
  },

  /** Shows the chosen photo as a card; without a photo, the drop zone. */
  preview() {
    const slot = document.getElementById("image-preview");
    const drop = document.getElementById("image-drop");
    if (!slot) return;
    drop?.classList.toggle("hidden", Boolean(this.file));
    if (!this.file) {
      slot.innerHTML = "";
      return;
    }
    slot.innerHTML = `<div class="photo-card">
        <img src="${this.dataUrl}" alt="Your photo">
        <div class="photo-card-body">
          <div class="row" style="justify-content:space-between">
            <span class="label">Your photo ▪ ${esc(this.file.name.slice(0, 32))}</span>
            <button type="button" class="link" data-remove-image>Remove</button>
          </div>
          <p class="photo-note">We're showing paintings that look like this photo.</p>
          <div class="photo-modes">
            <button type="button" class="text-link" data-photo-mode="similar">or find paintings similar to this photo</button>
            <button type="button" class="text-link" data-photo-mode="room">or let our curator pick paintings for this room</button>
          </div>
        </div>
      </div>`;
    slot.querySelector("[data-remove-image]").onclick = () => {
      this.file = null;
      this.dataUrl = null;
      this.preview();
    };
  },
};
