from PIL import Image
import os
import io
import sys


def resize_image(image, max_size):
    width, height = image.size
    ratio = min(max_size / width, max_size / height)
    new_width = int(width * ratio)
    new_height = int(height * ratio)
    return image.resize((new_width, new_height), Image.Resampling.LANCZOS)


def compress_image_to_target_size(image, target_size, output_path):
    quality = 100
    temp_image = image.copy()

    while True:
        buffer = io.BytesIO()
        temp_image.save(buffer, format="JPEG", quality=quality)
        buffer.seek(0)
        file_size = len(buffer.getvalue())

        if file_size <= target_size or quality <= 1:
            break

        quality -= 5

    with open(output_path, "wb") as output_file:
        output_file.write(buffer.getvalue())


def main(input_path, output_path, target_file_size, max_size):
    image = Image.open(input_path)
    resized_image = resize_image(image, max_size)
    compress_image_to_target_size(resized_image, target_file_size, output_path)

    # input_path = sys.argv[1]  # Path to the image to be resized
    # if not os.path.exists(input_path):
    #     print("Input file does not exist.")
    #     exit(1)

    # output_path = input_path  # Path to save the resized image
    # target_file_size = 500 * 1024  # Target file size in bytes (e.g., 100 KB)
    # # Maximum dimension (width or height) for the resized image
    # max_size = 1000
    # if os.path.getsize(input_path) <= target_file_size:
    #     print("Image is already smaller than the target size.")
    #     exit(0)
    # print(
    #     f"Resizing image to {target_file_size / 1024} KB... (before: {os.path.getsize(input_path) / 1024} KB)")
    # main(input_path, output_path, target_file_size, max_size)
    # print(
    #     f"Resized image saved to {output_path} (after: {os.path.getsize(output_path) / 1024} KB)")


def iterate_files_recursively(directory) -> list[str]:
    ret = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)

            ret.append(file_path)
    return ret


def change_all_files():
    target_file_size = 500 * 1024  # Target file size in bytes (e.g., 100 KB)
    max_size = 2000
    for file in iterate_files_recursively("assets/photos"):
        if file.endswith(".png") or file.endswith(".jpg") or file.endswith(".jpeg"):
            input_path = file  # Path to save the resized image
            output_path = file  # Path to save the resized image
            # Maximum dimension (width or height) for the resized image
            if os.path.getsize(input_path) <= target_file_size:
                print(
                    f"Image {input_path} is already smaller than the target size. (max: {target_file_size / 1024} KB)")
                continue
            print(
                f"Resizing image {input_path} to {target_file_size / 1024} KB... (before: {os.path.getsize(input_path) / 1024} KB)")
            main(input_path, output_path, target_file_size, max_size)
            print(
                f"Resized image saved to {output_path} (after: {os.path.getsize(output_path) / 1024} KB)")


if __name__ == "__main__":
    change_all_files()
