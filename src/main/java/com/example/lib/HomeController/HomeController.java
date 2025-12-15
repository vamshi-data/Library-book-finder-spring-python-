package com.example.lib.HomeController;

import java.util.concurrent.TimeUnit;

import com.example.lib.model.Book;
import java.nio.charset.StandardCharsets;


import com.example.lib.repository.BookRepository;
import lombok.RequiredArgsConstructor;

import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import com.example.lib.service.BookCheckService;
import java.util.Base64;



import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.io.File;

@Controller
@RequiredArgsConstructor
public class HomeController {

    private final BookRepository bookRepository;
    private final BookCheckService bookCheckService;

    @GetMapping("/home")
    public String home() {
        return "home";
    }
    
    @PostMapping("/home/upload")
public String uploadImage(@RequestParam("file") MultipartFile file, Model model)
        throws IOException {

    Book book = new Book();
    book.setOriginalImg(file.getBytes());
    bookRepository.save(book);

    // Save file physically for python usage
    Path tempFile = Paths.get(System.getProperty("java.io.tmpdir"),
                              "input_" + book.getId() + ".png");
    Files.write(tempFile, file.getBytes());

    // store path for python
    book.setInputPath(tempFile.toString());
    bookRepository.save(book);

    model.addAttribute("bookId", book.getId());
    return "home";
}
@PostMapping("/home/algo")
public String search(@RequestParam("query") String query,
                     @RequestParam("bookId") Long bookId,
                     Model model) {
 String jsonString = null; 
    try {
        Book book = bookRepository.findById(bookId).orElseThrow();

        String inputPath = book.getInputPath();
        String outputPath = System.getProperty("java.io.tmpdir")
                + File.separator + "output_" + book.getId() + ".png";

        String pythonExe = "G:/wepractice13oct/library/lib/venv/Scripts/python.exe";
        String scriptPath = "g:/wepractice13oct/library/lib/python/process_book.py";

        ProcessBuilder pb = new ProcessBuilder(
                pythonExe,
                scriptPath,
                inputPath,
                outputPath,
                query
        );

        pb.redirectErrorStream(true);
        Process process = pb.start();

        // Read ALL python output
        BufferedReader reader =
                new BufferedReader(new InputStreamReader(process.getInputStream(), StandardCharsets.UTF_8));

        StringBuilder pythonOutput = new StringBuilder();
        String line;
      StringBuilder jsonBuilder;
        jsonBuilder = new StringBuilder();
  boolean jsonMode;
        jsonMode = false;
      while ((line = reader.readLine()) != null) {
  
    if (line.equals("===JSON_START===")) {
         jsonMode = true;
        continue;
    }
    if (line.equals("===JSON_END===")) {
        break;
    }
    if (jsonMode) {
        jsonBuilder.append(line);
    }
    else {
        pythonOutput.append(line).append("\n");
    }}
        jsonString = jsonBuilder.toString();
reader.close();

        // Wait for process to finish with timeout


       boolean finished = process.waitFor(120, TimeUnit.SECONDS);
if (!finished) {
    process.destroyForcibly();
    throw new RuntimeException("Python OCR timed out");
}

int exitCode = process.exitValue();   // ✅ ADD THIS

if (exitCode != 0) {
    throw new RuntimeException("Python failed:\n" + pythonOutput);
}  
        Path outputFile = Paths.get(outputPath);
        if (!Files.exists(outputFile)) {
            throw new RuntimeException("Output image not created by Python");
        }

        byte[] outputBytes = Files.readAllBytes(outputFile);

        book.setOutputImg(outputBytes);
 
        book.setOcrJson(jsonString);
        bookRepository.save(book);

        model.addAttribute("searchResult", query);
        model.addAttribute("bookId", book.getId());

    } catch (Exception e) {
        e.printStackTrace();
        model.addAttribute("searchResult", "Error running OCR");
    }

    return "home";
}

@PostMapping("/home/check")
public String check(@RequestParam String text,
                    @RequestParam Long bookId,
                    Model model) {

    try {
        byte[] img =
                bookCheckService.checkFromJson(bookId, text);

        model.addAttribute(
                "outputImg",
                Base64.getEncoder().encodeToString(img)
        );
        model.addAttribute("bookId", bookId);
        model.addAttribute("searchText", text);

    } catch (Exception e) {
        e.printStackTrace();
        model.addAttribute("error", "Check failed");
    }

    return "home";
}

@GetMapping(value = "/home/image/{id}", produces = MediaType.IMAGE_PNG_VALUE)
@ResponseBody
public ResponseEntity<byte[]> loadImage(@PathVariable Long id, @RequestParam("type") String type) {
    Book book = bookRepository.findById(id).orElseThrow();
    byte[] image = "output".equals(type) ? book.getOutputImg() : book.getOriginalImg();

    if (image == null || image.length == 0) {
        return ResponseEntity.notFound().build();
    }

    return ResponseEntity.ok().contentType(org.springframework.http.MediaType.IMAGE_PNG).body(image);
}
@PostMapping("/home/delete")
public String deleteBook(@RequestParam("bookId") Long bookId) {

    bookRepository.deleteById(bookId);

    return "redirect:/home";   // go back to home page
}


}
