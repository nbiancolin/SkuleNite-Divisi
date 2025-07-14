import React, { useState } from "react";
import {
  Container,
  FileInput,
  Button,
  Title,
  Loader,
  Center,
  Text,
  Notification,
} from "@mantine/core";
import { Check, X, UploadCloud } from "lucide-react"; // alternative icon set
import axios from "axios";

export default function PartFormatterPage() {
  const [file, setFile] = useState<File | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleUpload = async () => {
    if (!file) return;

    setIsLoading(true);
    setError(null);
    setDownloadUrl(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await axios.post("http://localhost:8000/api/upload-mscz/", formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });

      setDownloadUrl(response.data.download_url); // e.g., { download_url: "http://..." }
    } catch (err: any) {
      console.error("Upload error:", err);
      setError(err.response?.data?.detail || "Upload failed.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Container size="sm" py="xl">
      <Title align="center" mb="xl">
        Upload and Process File
      </Title>

      <FileInput
        placeholder="Choose a file"
        label="Select file"
        icon={<UploadCloud size={18} />}
        value={file}
        onChange={setFile}
        accept="*/*"
        mb="md"
      />

      <Button
        onClick={handleUpload}
        disabled={!file || isLoading}
        fullWidth
        loading={isLoading}
      >
        Upload & Process
      </Button>

      {isLoading && (
        <Center mt="xl">
          <Loader size="lg" />
        </Center>
      )}

      {downloadUrl && (
        <Notification
          mt="xl"
          icon={<Check size={18} />}
          color="green"
          title="Success"
          onClose={() => setDownloadUrl(null)}
        >
          Your file has been processed.{" "}
          <a
            href={downloadUrl}
            download
            target="_blank"
            rel="noopener noreferrer"
          >
            Click here to download.
          </a>
        </Notification>
      )}

      {error && (
        <Notification
          mt="xl"
          icon={<X size={18} />}
          color="red"
          title="Error"
          onClose={() => setError(null)}
        >
          {error}
        </Notification>
      )}
    </Container>
  );
}
