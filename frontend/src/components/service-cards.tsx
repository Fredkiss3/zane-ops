import {
  Container,
  GitBranchIcon,
  Github,
  HardDrive,
  LinkIcon,
  Tag
} from "lucide-react";
import { cn } from "~/lib/utils";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle
} from "./ui/card";
import { Separator } from "./ui/separator";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger
} from "./ui/tooltip";

type DockerServiceCardProps = {
  name: string;
  image: string;
  url?: string;
  tag: string;
  updatedAt: string;
  volumeNumber?: number;
  status: "healthy" | "unhealthy" | "sleeping" | "undeployed";
};

export function DockerServiceCard({
  name,
  image,
  url,
  tag,
  updatedAt,
  volumeNumber = 0,
  status
}: DockerServiceCardProps) {
  return (
    <Card className="rounded-2xl flex flex-col h-[220px] bg-toggle relative">
      <TooltipProvider>
        <Tooltip delayDuration={0}>
          <TooltipTrigger asChild>
            <span className="absolute cursor-pointer flex h-4 w-4 -top-2 -right-2">
              {status !== "undeployed" && (
                <span
                  className={cn(
                    "animate-ping absolute inline-flex h-full w-full rounded-full  opacity-75",
                    {
                      "bg-green-400": status === "healthy",
                      "bg-red-400": status === "unhealthy",
                      "bg-secondary": status === "sleeping"
                    }
                  )}
                />
              )}

              <span
                className={cn(
                  "relative inline-flex rounded-full h-4 w-4 bg-green-500",
                  {
                    "bg-green-500": status === "healthy",
                    "bg-red-500": status === "unhealthy",
                    "bg-secondary": status === "sleeping",
                    "bg-gray-400": status === "undeployed"
                  }
                )}
              ></span>
            </span>
          </TooltipTrigger>
          <TooltipContent>
            <div>
              {status === "healthy" && "✅ "}
              {status === "sleeping" && "💤 "}
              {status === "unhealthy" && "❌ "}
              {status === "undeployed" && "⏳ "}
              {status}
            </div>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>

      <CardHeader className="p-0  pb-0  pt-4 px-6">
        <CardTitle className="flex gap-2 items-center">
          <Container className="flex-none" size={30} />
          <div className="w-[calc(100%-38px)]">
            <h1 className="text-lg leading-tight">{name}</h1>
            <p className="text-sm font-medium overflow-x-hidden text-ellipsis whitespace-nowrap text-gray-400 leading-tight">
              {image}
            </p>
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent className="flex  justify-end flex-grow gap-0.5 flex-col text-sm text-gray-400 p-6">
        {!!url && (
          <a
            href={url}
            target="_blank"
            className="text-sm flex items-center gap-2 text-link"
          >
            <LinkIcon className="flex-none" size={15} />{" "}
            <div className="whitespace-nowrap overflow-x-hidden  text-ellipsis ">
              {url}
            </div>
          </a>
        )}

        <p className="flex items-center gap-2">
          <Tag size={15} /> {tag}
        </p>
        <p className="flex gap-2 items-center">{updatedAt}</p>
      </CardContent>

      <>
        <Separator />
        <CardFooter className="p-0 text-gray-400 px-6 py-4 text-sm flex gap-2">
          <HardDrive size={20} /> {volumeNumber}
          {volumeNumber > 1 ? " Volumes" : " Volume"}
        </CardFooter>
      </>
    </Card>
  );
}

type GitServiceCardProps = {
  name: string;
  repository: string;
  url?: string;
  updatedAt: string;
  lastCommitMessage?: string;
  branchName: string;
  volumeNumber?: number;
  status: "healthy" | "unhealthy" | "sleeping" | "undeployed";
};

export function GitServiceCard({
  name,
  repository,
  url,
  updatedAt,
  lastCommitMessage,
  volumeNumber = 0,
  branchName,
  status
}: GitServiceCardProps) {
  return (
    <Card className="rounded-2xl bg-toggle relative">
      <TooltipProvider>
        <Tooltip delayDuration={0}>
          <TooltipTrigger asChild>
            <span className="absolute cursor-pointer flex h-4 w-4 -top-2 -right-2">
              {status !== "undeployed" && (
                <span
                  className={cn(
                    "animate-ping absolute inline-flex h-full w-full rounded-full  opacity-75",
                    {
                      "bg-green-400": status === "healthy",
                      "bg-red-400": status === "unhealthy",
                      "bg-secondary": status === "sleeping"
                    }
                  )}
                />
              )}

              <span
                className={cn(
                  "relative inline-flex rounded-full h-4 w-4 bg-green-500",
                  {
                    "bg-green-500": status === "healthy",
                    "bg-red-500": status === "unhealthy",
                    "bg-secondary": status === "sleeping",
                    "bg-gray-400": status === "undeployed"
                  }
                )}
              ></span>
            </span>
          </TooltipTrigger>
          <TooltipContent>
            <div>
              {status === "healthy" && "✅ "}
              {status === "sleeping" && "💤 "}
              {status === "unhealthy" && "❌ "}
              {status === "undeployed" && "⏳ "}
              {status}
            </div>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>

      <CardHeader className="p-0  pb-0  pt-4 px-6">
        <CardTitle className="flex gap-2 items-center">
          <Github className="flex-none" size={30} />
          <div className="w-[calc(100%-38px)]">
            <h1 className="text-lg leading-tight">{name}</h1>
            <p className="text-sm font-medium overflow-x-hidden text-ellipsis whitespace-nowrap text-gray-400 leading-tight">
              {repository}
            </p>
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent className="flex  gap-0.5 flex-col text-sm text-gray-400 p-0 px-6 py-6">
        <a
          href={url}
          target="_blank"
          className="text-sm flex items-center gap-2 text-link"
        >
          <LinkIcon className="flex-none" size={15} />{" "}
          <div className="whitespace-nowrap overflow-x-hidden  text-ellipsis ">
            {url}
          </div>
        </a>
        <p className="text-ellipsis overflow-x-hidden whitespace-nowrap">
          {lastCommitMessage}
        </p>
        <p className="flex gap-2 items-center">
          {updatedAt} on <GitBranchIcon size={15} /> {branchName}
        </p>
      </CardContent>
      <Separator />
      <CardFooter className="p-0 text-gray-400 px-6 py-3 text-sm flex gap-2">
        <HardDrive size={20} /> {volumeNumber}
        {volumeNumber > 1 ? " Volumes" : " Volume"}
      </CardFooter>
    </Card>
  );
}
