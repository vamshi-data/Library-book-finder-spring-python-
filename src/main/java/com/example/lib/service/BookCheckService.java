package com.example.lib.service;
import com.example.lib.model.Book;
import com.example.lib.repository.BookRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.TimeUnit;   


@Service
public class BookCheckService {

    @Autowired
    private BookRepository bookRepository;

    public byte[] checkFromJson(Long bookId, String searchText)
            throws Exception {

        Book book = bookRepository.findById(bookId)
                .orElseThrow(() -> new RuntimeException("Book not found"));

        // ---- write image to temp file ----
        Path imgPath = Files.createTempFile("book_img_", ".png");
        Files.write(imgPath, book.getOriginalImg());

        // ---- write JSON to temp file ----
        Path jsonPath = Files.createTempFile("book_json_", ".json");
        Files.writeString(jsonPath, book.getOcrJson(), StandardCharsets.UTF_8);

        Path outPath = Files.createTempFile("book_out_", ".png");

        String pythonExe = "G:/wepractice13oct/library/lib/venv/Scripts/python.exe";
        String script = "g:/wepractice13oct/library/lib/python/check.py";

        ProcessBuilder pb = new ProcessBuilder(
            pythonExe,
            script,
            imgPath.toString(),
            jsonPath.toString(),
            outPath.toString(),
            searchText
    );

    pb.redirectErrorStream(true);
    Process p = pb.start();

    // --- Capture Python output ---
    StringBuilder outputLog = new StringBuilder();
    try (BufferedReader br = new BufferedReader(new InputStreamReader(p.getInputStream()))) {
        String line;
        while ((line = br.readLine()) != null) {
            outputLog.append(line).append(System.lineSeparator());
        }
    }

    // --- Wait for Python to finish ---
    if (!p.waitFor(60, TimeUnit.SECONDS)) {
        p.destroyForcibly();
        throw new RuntimeException("Python timeout. Output:\n" + outputLog);
    }

    if (p.exitValue() != 0) {
        throw new RuntimeException("Python failed. Output:\n" + outputLog);
    }

    return Files.readAllBytes(outPath);
}
}
    
