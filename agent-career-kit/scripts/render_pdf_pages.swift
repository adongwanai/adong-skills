#!/usr/bin/env swift
import AppKit
import Foundation
import PDFKit

guard CommandLine.arguments.count == 3 else {
    fatalError("usage: render_pdf_pages.swift <pdf> <output-prefix>")
}

let pdfURL = URL(fileURLWithPath: CommandLine.arguments[1])
let outputPrefix = CommandLine.arguments[2]
guard let document = PDFDocument(url: pdfURL) else {
    fatalError("cannot open PDF: \(pdfURL.path)")
}

for pageIndex in 0..<document.pageCount {
    guard let page = document.page(at: pageIndex) else {
        fatalError("cannot read page \(pageIndex + 1)")
    }
    let bounds = page.bounds(for: .mediaBox)
    let image = page.thumbnail(
        of: NSSize(width: bounds.width * 2, height: bounds.height * 2),
        for: .mediaBox
    )
    guard
        let bitmap = NSBitmapImageRep(data: image.tiffRepresentation!),
        let png = bitmap.representation(using: .png, properties: [:])
    else {
        fatalError("cannot render page \(pageIndex + 1)")
    }
    let output = URL(fileURLWithPath: "\(outputPrefix)-\(pageIndex + 1).png")
    try png.write(to: output)
}
