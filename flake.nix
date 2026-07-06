{
  description = "Libbitcoinkernel Workshop";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-parts.url = "github:hercules-ci/flake-parts";
    devshell.url = "github:numtide/devshell";
  };

  outputs = inputs@{ flake-parts, ... }:
    flake-parts.lib.mkFlake { inherit inputs; } {
      imports = [
        inputs.devshell.flakeModule
      ];

      systems = [ "x86_64-linux" "aarch64-linux" "aarch64-darwin" "x86_64-darwin" ];
      perSystem = { config, self', inputs', pkgs, system, ... }: {
        devshells.default = with pkgs; {
          devshell.name = "Cashu Workshop";

          packages = [
            bitcoin
            uv
            pkg-config
          ] ++ lib.optionals stdenv.isDarwin [
          ];
        };
      };
    };
}
