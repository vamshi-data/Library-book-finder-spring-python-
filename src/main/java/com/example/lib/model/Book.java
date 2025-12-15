package com.example.lib.model;

import jakarta.persistence.*;
import lombok.Data;



@Entity
@Data
public class Book {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Lob
    private byte[] originalImg;

    @Lob
    private byte[] outputImg;
    @Lob
    @Column(columnDefinition = "LONGTEXT")
    private String ocrJson;

    private String inputPath;
    private String outputPath;

}
