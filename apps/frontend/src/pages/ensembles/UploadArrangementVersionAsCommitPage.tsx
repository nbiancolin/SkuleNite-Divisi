import { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  Container,
  FileInput,
  Button,
  Title,
  Center,
  Text,
  Notification,
  TextInput,
} from "@mantine/core";
import { X, UploadCloud } from "lucide-react";
import { apiService } from "../../services/apiService";
import type { Arrangement } from "../../services/apiService";

export default function UploadArrangementVersionFromCommitPage() {
  const { arrangementId = "0"} = useParams();
  const [arrangement, setArrangement] = useState<Arrangement |undefined>(undefined)
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [commitMessage, setCommitMessage] = useState<string>("");
  const [noConflicts, setNoConflicts] = useState<boolean>(true);

  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
      const fetchData = async () => {
        try {
          const [arrangementData, noConflictsData] = await Promise.all([
            apiService.getArrangementById(+arrangementId),
            apiService.checkScoreVersion(+arrangementId),
          ]);
          setArrangement(arrangementData);
          setNoConflicts(noConflictsData);
        } catch (err) {
          if (err instanceof Error) {
            setError(err.message);
          }
        }
      };
 
      if (arrangementId) {
        fetchData();
      }
    }, [arrangementId]);

  const handleUpload = async () => {
    if (!file) return;
    setIsUploading(true);
    try {
      // const commitResponse = 
      await apiService.createArrangementCommit(
        Number(arrangementId),
        file,
        commitMessage
      );
      navigate(`/app/arrangements/${arrangementId}`)
    } catch (err: any) {
      console.error("Upload error:", err);
      setError(err?.message || "Upload failed.");
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <Container size="sm" py="xl">
      <Title ta="center" mb="xl">
        {arrangement?.title}
      </Title>
      <Center>
        <Text> Upload score as a new commit, then create a version from that commit.</Text>
      </Center>
      { !noConflicts && (
        <Container size="md" mb="lg" mt="xs">
          <Alert
            color="yellow"
            title="Warning"
            mb='sm'
          >
           This arrangement has been updated since you last downloaded. 
           It is possible you may overwrite other people's progress.
           Please download and check this is the case!
          </Alert>
        </Container>
      )}
      <FileInput
        placeholder="Choose a file"
        label="Select file"
        leftSection={<UploadCloud size={18} />}
        value={file}
        onChange={setFile}
        accept="*/*"
        mb="md"
      />
      <TextInput
        label="Commit message (optional)"
        value={commitMessage}
        onChange={(e) => setCommitMessage(e.currentTarget.value)}
        placeholder="Describe this change"
        mt="md"
      />

      <Button
        mt="md"
        onClick={handleUpload}
        disabled={!file || isUploading}
        fullWidth
        loading={isUploading}
      >
        Upload New Commit
      </Button>
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