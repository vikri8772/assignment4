# A2 Item image – sequence diagram

How an admin uploads an image for a food item, with a preview in the browser before anything is saved.

````mermaid
sequenceDiagram
    actor Admin
    participant FormTemplate as admin/item_form.html
    participant PreviewJS as static/js/image_preview.js
    participant AdminController
    participant FoodItemRepository
    participant FoodItem
    participant Uploads as static/uploads/

    Admin->>FormTemplate: Choose image file
    FormTemplate->>PreviewJS: change event
    PreviewJS->>PreviewJS: check type (jpg/png) and size (≤ 5 MB)
    alt file OK
        PreviewJS-->>Admin: Show preview next to current image
    else file not OK
        PreviewJS-->>Admin: Show error and clear file field
    end

    opt Admin changes their mind
        Admin->>FormTemplate: Click "Remove" / choose another file
        FormTemplate-->>Admin: Preview reset, nothing saved
    end

    Admin->>AdminController: Click Save (form with image)
    AdminController->>AdminController: validate file again (type, size)
    alt file valid
        AdminController->>FoodItemRepository: getById(id)
        FoodItemRepository-->>AdminController: FoodItem
        AdminController->>Uploads: save file with generated unique name
        Uploads-->>AdminController: path
        AdminController->>FoodItem: set picturePath = path
        AdminController->>FoodItemRepository: update(item)
        FoodItemRepository-->>AdminController: Saved
        AdminController-->>Admin: Show item list with new image
    else file invalid
        AdminController-->>Admin: Show form with error message
    end
````
