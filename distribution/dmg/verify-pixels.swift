// Refuse an optimization that changes a single decoded sRGB pixel or dimension.
import Foundation
import CoreGraphics
import ImageIO

func pixels(_ path: String) -> (Int, Int, Data) {
    let source = CGImageSourceCreateWithURL(URL(fileURLWithPath: path) as CFURL, nil)!
    let image = CGImageSourceCreateImageAtIndex(source, 0, nil)!
    var bytes = [UInt8](repeating: 0, count: image.width * image.height * 4)
    bytes.withUnsafeMutableBytes { buffer in
        let context = CGContext(data: buffer.baseAddress!, width: image.width, height: image.height,
                                bitsPerComponent: 8, bytesPerRow: image.width * 4,
                                space: CGColorSpace(name: CGColorSpace.sRGB)!,
                                bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
        context.draw(image, in: CGRect(x: 0, y: 0, width: image.width, height: image.height))
    }
    return (image.width, image.height, Data(bytes))
}
let arguments = Array(CommandLine.arguments.dropFirst())
precondition(arguments.count > 0 && arguments.count % 2 == 0)
for offset in stride(from: 0, to: arguments.count, by: 2) {
    let before = pixels(arguments[offset]), after = pixels(arguments[offset + 1])
    guard before.0 == after.0 && before.1 == after.1 && before.2 == after.2 else {
        fatalError("PNG optimization changed pixels or dimensions")
    }
}
print("All optimized media decoded identically to the originals.")
