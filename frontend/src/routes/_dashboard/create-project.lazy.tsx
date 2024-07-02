import * as Form from "@radix-ui/react-form";
import { useMutation } from "@tanstack/react-query";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { AlertCircle } from "lucide-react";
import { type RequestInput, apiClient } from "~/api/client";
import { withAuthRedirect } from "~/components/helper/auth-redirect";

import { MetaTitle } from "~/components/meta-title";
import { Alert, AlertDescription, AlertTitle } from "~/components/ui/alert";
import { Button } from "~/components/ui/button";
import { Input } from "~/components/ui/input";
import { Textarea } from "~/components/ui/textarea";
import { getFormErrorsFromResponseData } from "~/lib/utils";
import { getCsrfTokenHeader } from "~/utils";

export const Route = createFileRoute("/_dashboard/create-project")({
  component: withAuthRedirect(CreateProject)
});

export function CreateProject() {
  const navigate = useNavigate();

  const { isPending, mutate, data } = useMutation({
    mutationFn: async (input: RequestInput<"post", "/api/projects/">) => {
      const { error, data } = await apiClient.POST("/api/projects/", {
        headers: {
          ...(await getCsrfTokenHeader())
        },
        body: input
      });

      if (error) return error;
      if (data) {
        navigate({ to: `/project/${data.slug}` });
        return;
      }
    }
  });

  const errors = getFormErrorsFromResponseData(data);

  return (
    <main>
      <MetaTitle title="Create Project" />
      <Form.Root
        action={(formData) => {
          mutate({
            slug: formData.get("slug")?.toString().trim(),
            description: formData.get("description")?.toString()
          });
        }}
        className="flex h-[60vh] flex-grow justify-center items-center"
      >
        <div className="card flex lg:w-[30%] md:w-[50%] w-full flex-col gap-3">
          <h1 className="text-3xl font-bold">New Project</h1>

          {errors.non_field_errors && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>Error</AlertTitle>
              <AlertDescription>{errors.non_field_errors}</AlertDescription>
            </Alert>
          )}
          <Form.Field className="my-2 flex flex-col gap-1" name="username">
            <Form.Label>Slug</Form.Label>
            <Form.Control asChild>
              <Input
                className="p-1.5"
                placeholder="Ex: Zaneops"
                name="slug"
                type="text"
              />
            </Form.Control>
            {errors.slug && (
              <Form.Message className="text-red-500 text-sm">
                {errors.slug}
              </Form.Message>
            )}
          </Form.Field>

          <Form.Field className="my-2 flex flex-col gap-1" name="username">
            <Form.Label>Description</Form.Label>
            <Form.Control asChild>
              <Textarea
                className="placeholder:text-gray-400"
                name="description"
                placeholder="Ex: A self hosted PaaS"
              />
            </Form.Control>
            {errors.description && (
              <Form.Message className="text-red-500 text-sm">
                {errors.description}
              </Form.Message>
            )}
          </Form.Field>

          <Form.Submit asChild>
            <Button className="lg:w-fit w-full lg:ml-auto p-3 rounded-lg">
              {isPending ? "Creating Project..." : " Create a new project"}
            </Button>
          </Form.Submit>
        </div>
      </Form.Root>
    </main>
  );
}
