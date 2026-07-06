{
  description = "Libbitcoinkernel Workshop";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-parts.url = "github:hercules-ci/flake-parts";
  };

  outputs = inputs@{ flake-parts, ... }:
    flake-parts.lib.mkFlake { inherit inputs; } {
      imports = [
        inputs.devshell.flakeModule
      ];

      systems = [ "x86_64-linux" "aarch64-linux" "aarch64-darwin" "x86_64-darwin" ];
      perSystem = { config, self', inputs', pkgs, system, ... }: {
        devshells.default = with pkgs; {
          devshell.name = "Libbitcoinkernel Workshop";

          packages = [
            python311
            pipx
            pkg-config
            docker
          ] ++ lib.optionals stdenv.isDarwin [
          ];
        };
      };
    };
}
