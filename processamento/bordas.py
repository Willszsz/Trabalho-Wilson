import cv2


def detectar_bordas(cinza, config):
    return cv2.Canny(cinza, config["canny_baixo"], config["canny_alto"])
