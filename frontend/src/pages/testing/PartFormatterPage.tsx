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
  Group,
  TextInput,
} from "@mantine/core";
import { Check, X, UploadCloud } from "lucide-react";
import axios from "axios";

export default function PartFormatterPage() {
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isFormatting, setIsFormatting] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // New states
  const [selectedStyle, setSelectedStyle] = useState<"jazz" | "broadway" | null>(null);
  const [showTitle, setShowTitle] = useState("");
  const [showNumber, setShowNumber] = useState("");

  const handleUpload = async () => {
    if (!file) return;

    setIsUploading(true);
    setError(null);
    setDownloadUrl(null);
    setSessionId(null);
    setSelectedStyle(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await axios.post("http://localhost:8000/api/upload-mscz/", formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });

      const id = response.data.session_id;
      if (!id) throw new Error("No session ID returned");
      setSessionId(id);
    } catch (err: any) {
      console.error("Upload error:", err);
      setError(err.response?.data?.detail || "Upload failed.");
    } finally {
      setIsUploading(false);
    }
  };

  const handleStyleSelect = (style: "jazz" | "broadway") => {
    setSelectedStyle(style);
  };

  const handleFormatRequest = async () => {
    if (!sessionId || !selectedStyle) return;

    if (selectedStyle === "broadway" && (!showTitle || !showNumber)) {
      setError("Please provide both show title and show number.");
      return;
    }

    setIsFormatting(true);
    setError(null);
    setDownloadUrl(null);

    try {
      const response = await axios.post("http://localhost:8000/api/format-mscz/", {
        session_id: sessionId,
        style: selectedStyle,
        ...(selectedStyle === "broadway" && {
          show_title: showTitle,
          show_number: showNumber,
        }),
      });

      setDownloadUrl(response.data.score_download_url);
    } catch (err: any) {
      console.error("Formatting error:", err);
      setError(err.response?.data?.detail || "Formatting failed.");
    } finally {
      setIsFormatting(false);
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
        disabled={!file || isUploading}
        fullWidth
        loading={isUploading}
      >
        Upload
      </Button>

      {sessionId && !isFormatting && !downloadUrl && !selectedStyle && (
        <Center mt="xl">
          <div>
            <Text mb="sm" align="center">
              Choose a style to format your file:
            </Text>
            <Group position="center">
              <Button onClick={() => handleStyleSelect("jazz")}>Jazz</Button>
              <Button onClick={() => handleStyleSelect("broadway")}>Broadway</Button>
            </Group>
          </div>
        </Center>
      )}

      {selectedStyle === "broadway" && (
        <Center mt="xl">
          <div style={{ width: "100%" }}>
            <Text mb="sm" align="center">
              Enter show details:
            </Text>
            <TextInput
              label="Show Title"
              value={showTitle}
              onChange={(e) => setShowTitle(e.currentTarget.value)}
              mb="md"
              required
            />
            <TextInput
              label="Show Number"
              value={showNumber}
              onChange={(e) => setShowNumber(e.currentTarget.value)}
              mb="md"
              required
            />
            <Button onClick={handleFormatRequest} fullWidth>
              Format Broadway File
            </Button>
          </div>
        </Center>
      )}

      {selectedStyle === "jazz" && (
        <Center mt="xl">
          <Button onClick={handleFormatRequest}>Format Jazz File</Button>
        </Center>
      )}

      {isFormatting && (
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
